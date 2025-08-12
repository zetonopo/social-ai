import redis.asyncio as redis
from typing import Optional
import json
import asyncio
from app.core.config import settings


class RedisClient:
    def __init__(self):
        self.redis: Optional[redis.Redis] = None
    
    async def initialize(self):
        """Initialize Redis connection."""
        return await self.connect()
    
    async def connect(self):
        """Connect to Redis."""
        try:
            self.redis = redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            # Test connection
            await self.redis.ping()
            print("Connected to Redis successfully")
            return True
        except Exception as e:
            print(f"Failed to connect to Redis: {e}")
            self.redis = None
            return False
    
    async def close(self):
        """Close Redis connection."""
        return await self.disconnect()
    
    async def disconnect(self):
        """Disconnect from Redis."""
        if self.redis:
            await self.redis.close()
            self.redis = None
    
    async def get(self, key: str) -> Optional[str]:
        """Get value by key."""
        if not self.redis:
            return None
        try:
            return await self.redis.get(key)
        except Exception as e:
            print(f"Redis GET error: {e}")
            return None
    
    async def set(self, key: str, value: str, expire: Optional[int] = None) -> bool:
        """Set key-value pair with optional expiration."""
        if not self.redis:
            return False
        try:
            await self.redis.set(key, value, ex=expire)
            return True
        except Exception as e:
            print(f"Redis SET error: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key."""
        if not self.redis:
            return False
        try:
            await self.redis.delete(key)
            return True
        except Exception as e:
            print(f"Redis DELETE error: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        if not self.redis:
            return False
        try:
            return await self.redis.exists(key)
        except Exception as e:
            print(f"Redis EXISTS error: {e}")
            return False
    
    async def incr(self, key: str, amount: int = 1) -> Optional[int]:
        """Increment counter."""
        if not self.redis:
            return None
        try:
            return await self.redis.incr(key, amount)
        except Exception as e:
            print(f"Redis INCR error: {e}")
            return None
    
    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration for key."""
        if not self.redis:
            return False
        try:
            await self.redis.expire(key, seconds)
            return True
        except Exception as e:
            print(f"Redis EXPIRE error: {e}")
            return False
    
    async def ttl(self, key: str) -> int:
        """Get time to live for key."""
        if not self.redis:
            return -1
        try:
            return await self.redis.ttl(key)
        except Exception as e:
            print(f"Redis TTL error: {e}")
            return -1
    
    async def hget(self, name: str, key: str) -> Optional[str]:
        """Get value from hash."""
        if not self.redis:
            return None
        try:
            return await self.redis.hget(name, key)
        except Exception as e:
            print(f"Redis HGET error: {e}")
            return None
    
    async def hset(self, name: str, key: str, value: str) -> bool:
        """Set value in hash."""
        if not self.redis:
            return False
        try:
            await self.redis.hset(name, key, value)
            return True
        except Exception as e:
            print(f"Redis HSET error: {e}")
            return False
    
    async def hgetall(self, name: str) -> dict:
        """Get all values from hash."""
        if not self.redis:
            return {}
        try:
            return await self.redis.hgetall(name)
        except Exception as e:
            print(f"Redis HGETALL error: {e}")
            return {}
    
    async def lpush(self, key: str, *values) -> Optional[int]:
        """Push values to left of list."""
        if not self.redis:
            return None
        try:
            return await self.redis.lpush(key, *values)
        except Exception as e:
            print(f"Redis LPUSH error: {e}")
            return None
    
    async def rpop(self, key: str) -> Optional[str]:
        """Pop value from right of list."""
        if not self.redis:
            return None
        try:
            return await self.redis.rpop(key)
        except Exception as e:
            print(f"Redis RPOP error: {e}")
            return None
    
    async def ttl(self, key: str) -> int:
        """Get time to live for key."""
        if not self.redis:
            return -2
        try:
            return await self.redis.ttl(key)
        except Exception as e:
            print(f"Redis TTL error: {e}")
            return -2
    
    async def scan_iter(self, pattern: str = "*", count: int = 1000):
        """Scan keys matching pattern."""
        if not self.redis:
            return []
        try:
            keys = []
            async for key in self.redis.scan_iter(match=pattern, count=count):
                keys.append(key)
            return keys
        except Exception as e:
            print(f"Redis SCAN_ITER error: {e}")
            return []


# Global Redis client instance
redis_client = RedisClient()


async def get_redis() -> RedisClient:
    """Dependency to get Redis client."""
    return redis_client
