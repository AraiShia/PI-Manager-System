"""
客户端缓存管理器 - 加速数据加载
"""
import json
import os
import time
from typing import Dict, Any, Optional, List

class CacheManager:
    """本地文件缓存管理器"""
    
    def __init__(self, cache_dir: str = None):
        if cache_dir is None:
            # 使用用户目录下的缓存文件夹
            cache_dir = os.path.join(os.path.expanduser('~'), '.pi_manager_cache')
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        
        # 内存缓存
        self._memory_cache: Dict[str, Any] = {}
        self._cache_time: Dict[str, float] = {}
        
    def _get_file_path(self, key: str) -> str:
        """获取缓存文件路径"""
        # 将key中的特殊字符替换为安全字符
        safe_key = key.replace('/', '_').replace('\\', '_').replace(':', '_')
        return os.path.join(self.cache_dir, f"{safe_key}.json")
    
    def get(self, key: str, max_age: int = 300) -> Optional[Any]:
        """
        获取缓存数据
        
        Args:
            key: 缓存键
            max_age: 最大缓存时间（秒），默认5分钟
        
        Returns:
            缓存数据或None
        """
        # 先检查内存缓存
        if key in self._memory_cache:
            if time.time() - self._cache_time.get(key, 0) < max_age:
                return self._memory_cache[key]
            else:
                # 内存缓存过期
                del self._memory_cache[key]
                del self._cache_time[key]
        
        # 检查文件缓存
        file_path = self._get_file_path(key)
        if os.path.exists(file_path):
            try:
                # 检查文件修改时间
                mtime = os.path.getmtime(file_path)
                if time.time() - mtime < max_age:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        # 加载到内存缓存
                        self._memory_cache[key] = data
                        self._cache_time[key] = mtime
                        return data
                else:
                    # 文件缓存过期，删除
                    os.remove(file_path)
            except Exception as e:
                print(f"读取缓存失败 {key}: {e}")
                if os.path.exists(file_path):
                    os.remove(file_path)
        
        return None
    
    def set(self, key: str, data: Any):
        """
        设置缓存数据
        
        Args:
            key: 缓存键
            data: 缓存数据
        """
        # 保存到内存
        self._memory_cache[key] = data
        self._cache_time[key] = time.time()
        
        # 保存到文件
        file_path = self._get_file_path(key)
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, default=str)
        except Exception as e:
            print(f"写入缓存失败 {key}: {e}")
    
    def delete(self, key: str):
        """删除缓存"""
        # 删除内存缓存
        if key in self._memory_cache:
            del self._memory_cache[key]
            del self._cache_time[key]
        
        # 删除文件缓存
        file_path = self._get_file_path(key)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass
    
    def clear(self):
        """清空所有缓存"""
        # 清空内存
        self._memory_cache.clear()
        self._cache_time.clear()
        
        # 清空文件
        for filename in os.listdir(self.cache_dir):
            if filename.endswith('.json'):
                try:
                    os.remove(os.path.join(self.cache_dir, filename))
                except OSError:
                    pass
    
    def clear_expired(self, max_age: int = 300):
        """清理过期缓存"""
        now = time.time()
        
        # 清理内存
        expired_keys = [k for k, t in self._cache_time.items() if now - t > max_age]
        for key in expired_keys:
            del self._memory_cache[key]
            del self._cache_time[key]
        
        # 清理文件
        for filename in os.listdir(self.cache_dir):
            if filename.endswith('.json'):
                file_path = os.path.join(self.cache_dir, filename)
                try:
                    if now - os.path.getmtime(file_path) > max_age:
                        os.remove(file_path)
                except OSError:
                    pass


# 全局缓存实例
cache_manager = CacheManager()

# 缓存键常量
CACHE_KEYS = {
    'PRODUCTS': 'products',
    'CUSTOMERS': 'customers',
    'SUPPLIERS': 'suppliers',
    'INVENTORY_SUMMARY': 'inventory_summary',
    'CATEGORIES': 'categories',
    'PI_LIST': 'pi_list'
}


# 为了兼容 cached_client.py，添加别名方法
def set_user(user_id: str):
    """设置当前用户（用于隔离不同用户的缓存）"""
    # 当前实现不需要用户隔离，留空兼容
    pass

def is_cache_valid(key: str, max_age: int = 3600) -> bool:
    """检查缓存是否有效"""
    return cache_manager.get(key, max_age) is not None

def set_cache(key: str, data: Any, ttl: int = 3600):
    """设置缓存（兼容接口）"""
    cache_manager.set(key, data)

def get_cache(key: str) -> Optional[Any]:
    """获取缓存（兼容接口）"""
    return cache_manager.get(key)

def invalidate_cache(key: str):
    """使缓存失效（兼容接口）"""
    cache_manager.delete(key)

def clear_all_cache():
    """清空所有缓存（兼容接口）"""
    cache_manager.clear()

def get_cache_status() -> Dict[str, Any]:
    """获取缓存状态"""
    return {
        'memory_size': len(cache_manager._memory_cache),
        'cache_dir': cache_manager.cache_dir
    }

def find_by_index(key: str, item_id: str) -> Optional[Any]:
    """通过ID查找缓存项"""
    data = cache_manager.get(key)
    if data and isinstance(data, list):
        for item in data:
            if str(item.get('id')) == item_id:
                return item
    return None

def search_by_keyword(key: str, keyword: str) -> Optional[List[Any]]:
    """按关键词搜索缓存"""
    data = cache_manager.get(key)
    if data and isinstance(data, list):
        results = []
        keyword_lower = keyword.lower()
        for item in data:
            # 搜索常见字段
            for field in ['product_code', 'oe_number', 'customer_code', 'customer_name', 'supplier_code', 'supplier_name']:
                if keyword_lower in str(item.get(field, '')).lower():
                    results.append(item)
                    break
        return results if results else None
    return None
