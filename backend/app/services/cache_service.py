from typing import Optional, Any, List
import json
from datetime import datetime, timedelta
from app.core.redis_client import RedisClient


class CacheService:
    def __init__(self, redis_client: RedisClient):
        self.redis = redis_client
    
    async def cache_user_subscription(self, user_id: int, subscription_data: dict, expire_seconds: int = 3600):
        """Cache user subscription data."""
        key = f"user_subscription:{user_id}"
        value = json.dumps(subscription_data, default=str)
        await self.redis.set(key, value, expire_seconds)
    
    async def get_cached_user_subscription(self, user_id: int) -> Optional[dict]:
        """Get cached user subscription data."""
        key = f"user_subscription:{user_id}"
        cached_data = await self.redis.get(key)
        if cached_data:
            try:
                return json.loads(cached_data)
            except json.JSONDecodeError:
                return None
        return None
    
    async def cache_user_usage_stats(self, user_id: int, usage_data: dict, expire_seconds: int = 1800):
        """Cache user usage statistics."""
        key = f"user_usage:{user_id}"
        value = json.dumps(usage_data, default=str)
        await self.redis.set(key, value, expire_seconds)
    
    async def get_cached_user_usage_stats(self, user_id: int) -> Optional[dict]:
        """Get cached user usage statistics."""
        key = f"user_usage:{user_id}"
        cached_data = await self.redis.get(key)
        if cached_data:
            try:
                return json.loads(cached_data)
            except json.JSONDecodeError:
                return None
        return None
    
    async def cache_plans(self, plans_data: List[dict], expire_seconds: int = 7200):
        """Cache available plans."""
        key = "available_plans"
        value = json.dumps(plans_data, default=str)
        await self.redis.set(key, value, expire_seconds)
    
    async def get_cached_plans(self) -> Optional[List[dict]]:
        """Get cached plans."""
        key = "available_plans"
        cached_data = await self.redis.get(key)
        if cached_data:
            try:
                return json.loads(cached_data)
            except json.JSONDecodeError:
                return None
        return None
    
    async def get_user_subscription(self, user_id: int) -> Optional[dict]:
        """Get cached user subscription info."""
        key = f"user_subscription:{user_id}"
        cached_data = await self.redis.get(key)
        if cached_data:
            try:
                return json.loads(cached_data)
            except json.JSONDecodeError:
                return None
        return None
    
    async def cache_user_subscription(self, user_id: int, subscription_data: dict, expire_seconds: int = 3600):
        """Cache user subscription info."""
        key = f"user_subscription:{user_id}"
        value = json.dumps(subscription_data, default=str)
        await self.redis.set(key, value)
        await self.redis.expire(key, expire_seconds)
    
    async def invalidate_user_cache(self, user_id: int):
        """Invalidate all cache data for a user."""
        keys_to_delete = [
            f"user_subscription:{user_id}",
            f"user_usage:{user_id}",
            f"rate_limit:{user_id}:*"
        ]
        
        for key in keys_to_delete:
            if "*" in key:
                # For pattern matching, we'd need to implement pattern deletion
                # For now, we'll handle this in the rate limiting service
                continue
            await self.redis.delete(key)
    
    async def cache_system_stats(self, stats_data: dict, expire_seconds: int = 600):
        """Cache system-wide statistics."""
        key = "system_stats"
        value = json.dumps(stats_data, default=str)
        await self.redis.set(key, value, expire_seconds)
    
    async def get_cached_system_stats(self) -> Optional[dict]:
        """Get cached system statistics."""
        key = "system_stats"
        cached_data = await self.redis.get(key)
        if cached_data:
            try:
                return json.loads(cached_data)
            except json.JSONDecodeError:
                return None
        return None
    
    async def set_session(self, session_id: str, user_data: dict, expire_seconds: int = 86400):
        """Set user session data."""
        key = f"session:{session_id}"
        value = json.dumps(user_data, default=str)
        await self.redis.set(key, value, expire_seconds)
    
    async def get_session(self, session_id: str) -> Optional[dict]:
        """Get user session data."""
        key = f"session:{session_id}"
        cached_data = await self.redis.get(key)
        if cached_data:
            try:
                return json.loads(cached_data)
            except json.JSONDecodeError:
                return None
        return None
    
    async def delete_session(self, session_id: str):
        """Delete user session."""
        key = f"session:{session_id}"
        await self.redis.delete(key)
