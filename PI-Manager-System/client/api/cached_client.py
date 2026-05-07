import time
from typing import Optional, List, Dict, Any
from .client import ApiClient
from cache_manager import cache_manager

class CachedApiClient(ApiClient):
    def __init__(self, base_url: str = None, cache_ttl: int = 3600):
        super().__init__(base_url)
        self.cache_ttl = cache_ttl
        self.last_sync_time = {}
        self.update_listeners = []
        self.current_user = None  # 当前登录用户
        self.token = None  # 认证token
    
    def login(self, username: str, password: str) -> Dict:
        """用户登录"""
        response = requests.post(
            f"{self.base_url}/api/auth/login",
            params={"username": username, "password": password},
            timeout=30
        )
        response.raise_for_status()
        result = response.json()
        
        self.token = result["token"]
        self.current_user = result["user"]
        
        # 设置缓存管理器的用户ID
        cache_manager.set_user(str(self.current_user["id"]))
        
        return result
    
    def logout(self):
        """用户登出"""
        self.token = None
        self.current_user = None
        cache_manager.set_user(None)
    
    def add_update_listener(self, listener):
        """添加更新监听器"""
        self.update_listeners.append(listener)
    
    def notify_update(self, key: str, data: Any):
        """通知所有监听器数据已更新"""
        for listener in self.update_listeners:
            try:
                listener(key, data)
            except Exception as e:
                print(f"通知监听器失败: {e}")
    
    def _get_with_cache(self, cache_key: str, fetch_func, force_refresh: bool = False) -> Any:
        """带缓存的获取方法"""
        # 如果强制刷新或缓存无效，则从服务端获取
        if force_refresh or not cache_manager.is_cache_valid(cache_key):
            try:
                data = fetch_func()
                cache_manager.set_cache(cache_key, data, self.cache_ttl)
                self.last_sync_time[cache_key] = time.time()
                self.notify_update(cache_key, data)
                return data
            except Exception as e:
                # 如果获取失败，返回缓存数据（如果有）
                cached_data = cache_manager.get_cache(cache_key)
                if cached_data:
                    print(f"获取失败，使用缓存: {e}")
                    return cached_data
                raise
        # 否则返回缓存数据
        return cache_manager.get_cache(cache_key)
    
    def check_server_update(self, cache_key: str) -> bool:
        """检查服务端是否有更新"""
        # 实现检查逻辑（可以通过时间戳或版本号）
        # 这里简单实现为：超过TTL时间就认为需要更新
        return not cache_manager.is_cache_valid(cache_key)
    
    def sync_all(self):
        """同步所有缓存数据"""
        cache_keys = ["products", "customers", "suppliers", "pi_orders", "purchase_orders"]
        for key in cache_keys:
            if self.check_server_update(key):
                self._get_with_cache(key, getattr(self, f"_fetch_{key.replace('_', '')}", lambda: []))
    
    def invalidate_all(self):
        """使所有缓存失效"""
        cache_manager.clear_all_cache()
    
    # ==================== 产品相关 ====================
    
    def get_products(self, db_config: Dict = None, force_refresh: bool = False) -> List[Dict]:
        if db_config:
            self.set_db_config(db_config)
        
        # 使用类名显式调用父类方法，避免嵌套函数中super()的问题
        def fetch():
            return ApiClient.get_products(self)
        
        return self._get_with_cache("products", fetch, force_refresh)
    
    def search_products(self, keyword: str = "", category_id: int = None, status: int = None) -> List[Dict]:
        # 先尝试本地搜索
        if not keyword and category_id is None and status is None:
            return self.get_products()
        
        # 使用索引快速查找
        if keyword:
            cached = cache_manager.get_cache("products")
            if cached:
                results = cache_manager.search_by_keyword("products", keyword)
                if results:
                    return results
        
        # 如果本地搜索没有结果或需要更精确的搜索，调用服务端
        return super().search_products(keyword, category_id, status)
    
    def get_product_detail(self, product_id: int) -> Dict:
        # 先尝试从缓存中查找
        product = cache_manager.find_by_index("products", str(product_id))
        if product:
            return product
        # 如果缓存中没有，调用服务端
        return super().get_product_detail(product_id)
    
    def create_product(self, data: Dict) -> Dict:
        result = super().create_product(data)
        # 使产品缓存失效
        cache_manager.invalidate_cache("products")
        return result
    
    def update_product(self, product_id: int, data: Dict) -> Dict:
        result = super().update_product(product_id, data)
        # 使产品缓存失效
        cache_manager.invalidate_cache("products")
        return result
    
    def delete_product(self, product_id: int) -> Dict:
        result = super().delete_product(product_id)
        # 使产品缓存失效
        cache_manager.invalidate_cache("products")
        return result
    
    # ==================== 客户相关 ====================
    
    def get_customers(self, force_refresh: bool = False) -> List[Dict]:
        def fetch():
            return ApiClient.get_customers(self)
        
        return self._get_with_cache("customers", fetch, force_refresh)
    
    def search_customers(self, keyword: str = "", country: str = None) -> List[Dict]:
        # 先尝试本地搜索
        if not keyword and not country:
            return self.get_customers()
        
        # 使用索引快速查找
        if keyword:
            cached = cache_manager.get_cache("customers")
            if cached:
                results = cache_manager.search_by_keyword("customers", keyword)
                if results:
                    return results
        
        return super().search_customers(keyword, country)
    
    def get_customer_detail(self, customer_id: int) -> Dict:
        # 先尝试从缓存中查找
        customer = cache_manager.find_by_index("customers", str(customer_id))
        if customer:
            return customer
        return super().get_customer_detail(customer_id)
    
    def create_customer(self, data: Dict) -> Dict:
        result = super().create_customer(data)
        cache_manager.invalidate_cache("customers")
        return result
    
    def update_customer(self, customer_id: int, data: Dict) -> Dict:
        result = super().update_customer(customer_id, data)
        cache_manager.invalidate_cache("customers")
        return result
    
    def delete_customer(self, customer_id: int) -> Dict:
        result = super().delete_customer(customer_id)
        cache_manager.invalidate_cache("customers")
        return result
    
    # ==================== 供应商相关 ====================
    
    def get_suppliers(self, force_refresh: bool = False) -> List[Dict]:
        def fetch():
            return ApiClient.get_suppliers(self)
        
        return self._get_with_cache("suppliers", fetch, force_refresh)
    
    def get_supplier_detail(self, supplier_id: int) -> Dict:
        supplier = cache_manager.find_by_index("suppliers", str(supplier_id))
        if supplier:
            return supplier
        return super().get_supplier_detail(supplier_id)
    
    def create_supplier(self, data: Dict) -> Dict:
        result = super().create_supplier(data)
        cache_manager.invalidate_cache("suppliers")
        return result
    
    def update_supplier(self, supplier_id: int, data: Dict) -> Dict:
        result = super().update_supplier(supplier_id, data)
        cache_manager.invalidate_cache("suppliers")
        return result
    
    def delete_supplier(self, supplier_id: int) -> Dict:
        result = super().delete_supplier(supplier_id)
        cache_manager.invalidate_cache("suppliers")
        return result
    
    # ==================== PI订单相关 ====================
    
    def get_pi_orders(self, force_refresh: bool = False) -> List[Dict]:
        def fetch():
            return ApiClient.get_pi_orders(self)
        
        return self._get_with_cache("pi_orders", fetch, force_refresh)
    
    def create_pi(self, data: Dict) -> Dict:
        result = super().create_pi(data)
        cache_manager.invalidate_cache("pi_orders")
        return result
    
    def update_pi(self, pi_id: int, data: Dict) -> Dict:
        result = super().update_pi(pi_id, data)
        cache_manager.invalidate_cache("pi_orders")
        return result
    
    # ==================== 采购单相关 ====================
    
    def get_purchase_orders(self, force_refresh: bool = False) -> List[Dict]:
        def fetch():
            return ApiClient.get_purchase_orders(self)
        
        return self._get_with_cache("purchase_orders", fetch, force_refresh)
    
    def create_purchase(self, data: Dict) -> Dict:
        result = super().create_purchase(data)
        cache_manager.invalidate_cache("purchase_orders")
        return result
    
    def update_purchase(self, po_id: int, data: Dict) -> Dict:
        result = super().update_purchase(po_id, data)
        cache_manager.invalidate_cache("purchase_orders")
        return result
    
    # 获取缓存状态
    def get_cache_status(self) -> Dict[str, Any]:
        return cache_manager.get_cache_status()
