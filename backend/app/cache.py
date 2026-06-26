"""
缓存模块 - 使用内存缓存提高数据库查询速度
"""
from functools import wraps
from typing import Optional, Any, Callable
import time
import threading

class MemoryCache:
    """线程安全的内存缓存"""
    def __init__(self):
        self._cache = {}
        self._lock = threading.RLock()
        self._stats = {'hits': 0, 'misses': 0}
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        with self._lock:
            if key in self._cache:
                value, expiry = self._cache[key]
                if expiry is None or time.time() < expiry:
                    self._stats['hits'] += 1
                    return value
                else:
                    # 过期删除
                    del self._cache[key]
            self._stats['misses'] += 1
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """设置缓存值，ttl为秒"""
        with self._lock:
            expiry = time.time() + ttl if ttl else None
            self._cache[key] = (value, expiry)
    
    def delete(self, key: str):
        """删除缓存"""
        with self._lock:
            self._cache.pop(key, None)
    
    def clear(self):
        """清空缓存"""
        with self._lock:
            self._cache.clear()
    
    def clear_prefix(self, prefix: str):
        """清空指定前缀的缓存"""
        with self._lock:
            keys_to_delete = [k for k in self._cache.keys() if k.startswith(prefix)]
            for k in keys_to_delete:
                del self._cache[k]
    
    def get_stats(self) -> dict:
        """获取缓存统计"""
        with self._lock:
            total = self._stats['hits'] + self._stats['misses']
            hit_rate = (self._stats['hits'] / total * 100) if total > 0 else 0
            return {
                'hits': self._stats['hits'],
                'misses': self._stats['misses'],
                'total': total,
                'hit_rate': f"{hit_rate:.1f}%",
                'size': len(self._cache)
            }

# 全局缓存实例
cache = MemoryCache()

def cached(ttl: Optional[int] = 300, key_prefix: str = ""):
    """缓存装饰器
    
    Args:
        ttl: 缓存时间（秒），默认5分钟
        key_prefix: 缓存键前缀
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            cache_key = f"{key_prefix}:{func.__name__}:{str(args)}:{str(kwargs)}"
            
            # 尝试从缓存获取
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # 执行函数并缓存结果
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl)
            return result
        return wrapper
    return decorator

def invalidate_cache(key_prefix: str):
    """清除指定前缀的缓存"""
    cache.clear_prefix(key_prefix)

# 常用缓存键前缀
CACHE_KEYS = {
    'PRODUCT': 'product',
    'CUSTOMER': 'customer',
    'SUPPLIER': 'supplier',
    'PI': 'pi',
    'PRODUCT_SUPPLIER': 'product_supplier',
    'CATEGORY': 'category',
    'INVENTORY': 'inventory'
}
