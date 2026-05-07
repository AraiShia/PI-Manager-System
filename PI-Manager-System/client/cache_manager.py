import json
import os
import time
from datetime import datetime
from typing import Dict, List, Any, Optional

class CacheManager:
    def __init__(self, cache_dir: str = "cache"):
        self.cache_dir = cache_dir
        self.cache_data: Dict[str, Any] = {}
        self.cache_metadata: Dict[str, Dict[str, float]] = {}
        self.indexes: Dict[str, Dict[str, int]] = {}
        self.user_id: Optional[str] = None  # 当前用户ID，用于缓存隔离
        
        os.makedirs(cache_dir, exist_ok=True)
        self.load_cache()
    
    def set_user(self, user_id: str):
        """设置当前用户ID"""
        self.user_id = user_id
    
    def _get_cache_key(self, key: str) -> str:
        """生成带用户ID的缓存键"""
        if self.user_id:
            return f"user_{self.user_id}_{key}"
        return key
    
    def load_cache(self):
        """加载缓存文件"""
        try:
            # 加载数据缓存
            data_file = os.path.join(self.cache_dir, "data.json")
            if os.path.exists(data_file):
                with open(data_file, "r", encoding="utf-8") as f:
                    self.cache_data = json.load(f)
                    print(f"加载缓存数据: {len(self.cache_data)} 个条目")
            
            # 加载元数据
            meta_file = os.path.join(self.cache_dir, "metadata.json")
            if os.path.exists(meta_file):
                with open(meta_file, "r", encoding="utf-8") as f:
                    self.cache_metadata = json.load(f)
                    print(f"加载缓存元数据: {len(self.cache_metadata)} 个条目")
            
            # 加载索引
            index_file = os.path.join(self.cache_dir, "indexes.json")
            if os.path.exists(index_file):
                with open(index_file, "r", encoding="utf-8") as f:
                    self.indexes = json.load(f)
                    print(f"加载缓存索引: {len(self.indexes)} 个条目")
        except json.JSONDecodeError as e:
            print(f"缓存文件格式错误，将重新创建: {e}")
            self.cache_data = {}
            self.cache_metadata = {}
            self.indexes = {}
        except Exception as e:
            print(f"加载缓存失败: {e}")
            import traceback
            traceback.print_exc()
    
    def save_cache(self):
        """保存缓存到文件"""
        try:
            # 保存数据缓存
            data_file = os.path.join(self.cache_dir, "data.json")
            with open(data_file, "w", encoding="utf-8") as f:
                json.dump(self.cache_data, f, ensure_ascii=False, indent=2)
            
            # 保存元数据
            meta_file = os.path.join(self.cache_dir, "metadata.json")
            with open(meta_file, "w", encoding="utf-8") as f:
                json.dump(self.cache_metadata, f, ensure_ascii=False, indent=2)
            
            # 保存索引
            index_file = os.path.join(self.cache_dir, "indexes.json")
            with open(index_file, "w", encoding="utf-8") as f:
                json.dump(self.indexes, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存缓存失败: {e}")
    
    def get_cache(self, key: str) -> Optional[Any]:
        """获取缓存数据"""
        cache_key = self._get_cache_key(key)
        return self.cache_data.get(cache_key)
    
    def set_cache(self, key: str, data: Any, ttl: int = 3600):
        """设置缓存数据"""
        cache_key = self._get_cache_key(key)
        self.cache_data[cache_key] = data
        self.cache_metadata[cache_key] = {
            "timestamp": time.time(),
            "ttl": ttl
        }
        self.build_index(cache_key, data)
    
    def is_cache_valid(self, key: str) -> bool:
        """检查缓存是否有效"""
        cache_key = self._get_cache_key(key)
        meta = self.cache_metadata.get(cache_key)
        if not meta:
            return False
        return time.time() < meta["timestamp"] + meta["ttl"]
    
    def invalidate_cache(self, key: str):
        """使缓存失效"""
        cache_key = self._get_cache_key(key)
        if cache_key in self.cache_data:
            del self.cache_data[cache_key]
        if cache_key in self.cache_metadata:
            del self.cache_metadata[cache_key]
        if cache_key in self.indexes:
            del self.indexes[cache_key]
    
    def build_index(self, key: str, data: Any):
        """为数据建立索引"""
        if isinstance(data, list):
            index = {}
            for i, item in enumerate(data):
                if isinstance(item, dict):
                    # 为常用字段建立索引
                    if "id" in item:
                        index[str(item["id"])] = i
                    if "name" in item:
                        index[item["name"]] = i
                    if "code" in item:
                        index[item["code"]] = i
            self.indexes[key] = index
    
    def find_by_index(self, key: str, field_value: str) -> Optional[Any]:
        """通过索引查找数据"""
        cache_key = self._get_cache_key(key)
        if cache_key not in self.indexes or cache_key not in self.cache_data:
            return None
        
        index = self.indexes[cache_key]
        if field_value in index:
            idx = index[field_value]
            return self.cache_data[cache_key][idx]
        return None
    
    def search_by_keyword(self, key: str, keyword: str) -> List[Any]:
        """在缓存中搜索关键词"""
        cache_key = self._get_cache_key(key)
        if cache_key not in self.cache_data:
            return []
        
        data = self.cache_data[cache_key]
        results = []
        
        for item in data:
            if isinstance(item, dict):
                for value in item.values():
                    if isinstance(value, str) and keyword.lower() in value.lower():
                        results.append(item)
                        break
        return results
    
    def clear_all_cache(self):
        """清空所有缓存"""
        self.cache_data = {}
        self.cache_metadata = {}
        self.indexes = {}
        self.save_cache()
    
    def get_cache_status(self) -> Dict[str, Any]:
        """获取缓存状态信息"""
        status = {
            "cache_count": len(self.cache_data),
            "index_count": len(self.indexes),
            "total_size": 0,
            "entries": []
        }
        
        for key, data in self.cache_data.items():
            size = len(json.dumps(data, ensure_ascii=False))
            status["total_size"] += size
            status["entries"].append({
                "key": key,
                "count": len(data) if isinstance(data, list) else 1,
                "size": size,
                "valid": self.is_cache_valid(key)
            })
        
        return status

# 创建全局缓存实例
cache_manager = CacheManager()
