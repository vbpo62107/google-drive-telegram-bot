"""用户数据缓存系统"""
import time
from typing import Dict, Any, Optional


class UserVideoCache:
    """用户视频信息缓存（5分钟过期）"""
    
    def __init__(self, ttl: int = 300):
        self.data: Dict[int, Dict[str, Any]] = {}
        self.ttl = ttl
    
    def set(self, user_id: int, video_info: Dict[str, Any]):
        """存储用户的视频信息"""
        self.data[user_id] = {
            'info': video_info,
            'timestamp': time.time()
        }
    
    def get(self, user_id: int) -> Optional[Dict[str, Any]]:
        """获取用户的视频信息"""
        if user_id not in self.data:
            return None
        
        entry = self.data[user_id]
        
        if time.time() - entry['timestamp'] > self.ttl:
            del self.data[user_id]
            return None
        
        return entry['info']
    
    def clear(self, user_id: int):
        """清除用户的数据"""
        if user_id in self.data:
            del self.data[user_id]


# 全局缓存实例
video_cache = UserVideoCache()
