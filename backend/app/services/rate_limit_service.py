from typing import Optional, Tuple
from datetime import datetime, timedelta
import asyncio
from fastapi import HTTPException, status
from app.core.redis_client import RedisClient
from app.models.user import User, Plan
from sqlalchemy.orm import Session


class RateLimitService:
    def __init__(self, redis_client: RedisClient):
        self.redis = redis_client
    
    async def check_rate_limit(self, user: User, plan: Plan) -> Tuple[bool, dict]:
        """
        Check if user has exceeded rate limit.
        Returns (is_allowed, rate_limit_info)
        """
        now = datetime.utcnow()
        
        # Create keys for different time windows
        minute_key = f"rate_limit:{user.id}:minute:{now.strftime('%Y%m%d%H%M')}"
        hour_key = f"rate_limit:{user.id}:hour:{now.strftime('%Y%m%d%H')}"
        day_key = f"rate_limit:{user.id}:day:{now.strftime('%Y%m%d')}"
        month_key = f"rate_limit:{user.id}:month:{now.strftime('%Y%m')}"
        
        # Get current counts
        minute_count = await self.redis.get(minute_key) or "0"
        hour_count = await self.redis.get(hour_key) or "0"
        day_count = await self.redis.get(day_key) or "0"
        month_count = await self.redis.get(month_key) or "0"
        
        minute_count = int(minute_count)
        hour_count = int(hour_count)
        day_count = int(day_count)
        month_count = int(month_count)
        
        # Define limits based on plan
        limits = self._get_plan_limits(plan)
        
        # Check limits
        rate_limit_info = {
            "requests_per_minute": minute_count,
            "requests_per_hour": hour_count,
            "requests_per_day": day_count,
            "requests_per_month": month_count,
            "limits": limits,
            "reset_times": {
                "minute": (now + timedelta(minutes=1)).replace(second=0, microsecond=0),
                "hour": (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0),
                "day": (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0),
                "month": self._get_next_month_start(now)
            }
        }
        
        # Check each limit
        if minute_count >= limits["per_minute"]:
            return False, rate_limit_info
        
        if hour_count >= limits["per_hour"]:
            return False, rate_limit_info
        
        if day_count >= limits["per_day"]:
            return False, rate_limit_info
        
        if month_count >= limits["per_month"]:
            return False, rate_limit_info
        
        return True, rate_limit_info
    
    async def increment_usage(self, user_id: int) -> dict:
        """Increment usage counters for all time windows."""
        now = datetime.utcnow()
        
        # Create keys for different time windows
        minute_key = f"rate_limit:{user_id}:minute:{now.strftime('%Y%m%d%H%M')}"
        hour_key = f"rate_limit:{user_id}:hour:{now.strftime('%Y%m%d%H')}"
        day_key = f"rate_limit:{user_id}:day:{now.strftime('%Y%m%d')}"
        month_key = f"rate_limit:{user_id}:month:{now.strftime('%Y%m')}"
        
        # Increment counters
        minute_count = await self.redis.incr(minute_key) or 1
        hour_count = await self.redis.incr(hour_key) or 1
        day_count = await self.redis.incr(day_key) or 1
        month_count = await self.redis.incr(month_key) or 1
        
        # Set expiration for keys if they're new
        if minute_count == 1:
            await self.redis.expire(minute_key, 60)
        if hour_count == 1:
            await self.redis.expire(hour_key, 3600)
        if day_count == 1:
            await self.redis.expire(day_key, 86400)
        if month_count == 1:
            # Set to expire at the end of next month
            next_month = self._get_next_month_start(now)
            expire_seconds = int((next_month - now).total_seconds())
            await self.redis.expire(month_key, expire_seconds)
        
        return {
            "minute": minute_count,
            "hour": hour_count,
            "day": day_count,
            "month": month_count
        }
    
    async def check_concurrent_requests(self, user_id: int, plan: Plan) -> bool:
        """Check if user has exceeded concurrent request limit."""
        concurrent_key = f"concurrent:{user_id}"
        current_concurrent = await self.redis.get(concurrent_key) or "0"
        current_concurrent = int(current_concurrent)
        
        if current_concurrent >= plan.concurrent_requests:
            return False
        
        return True
    
    async def acquire_concurrent_slot(self, user_id: int, request_id: str, expire_seconds: int = 300):
        """Acquire a concurrent request slot."""
        concurrent_key = f"concurrent:{user_id}"
        slot_key = f"concurrent_slot:{user_id}:{request_id}"
        
        # Add to concurrent counter
        await self.redis.incr(concurrent_key)
        await self.redis.expire(concurrent_key, expire_seconds)
        
        # Set slot marker
        await self.redis.set(slot_key, "1", expire_seconds)
    
    async def release_concurrent_slot(self, user_id: int, request_id: str):
        """Release a concurrent request slot."""
        concurrent_key = f"concurrent:{user_id}"
        slot_key = f"concurrent_slot:{user_id}:{request_id}"
        
        # Check if slot exists
        if await self.redis.exists(slot_key):
            # Decrease concurrent counter
            current = await self.redis.get(concurrent_key) or "0"
            current = max(0, int(current) - 1)
            
            if current > 0:
                await self.redis.set(concurrent_key, str(current), 300)
            else:
                await self.redis.delete(concurrent_key)
            
            # Remove slot marker
            await self.redis.delete(slot_key)
    
    def _get_plan_limits(self, plan: Plan) -> dict:
        """Get rate limits based on plan."""
        # Base limits
        base_limits = {
            "per_minute": min(plan.requests_per_month // (30 * 24 * 60), 100),  # Don't exceed 100/min
            "per_hour": min(plan.requests_per_month // (30 * 24), 6000),  # Don't exceed 6000/hour
            "per_day": min(plan.requests_per_month // 30, 144000),  # Don't exceed 144k/day
            "per_month": plan.requests_per_month
        }
        
        # Ensure reasonable minimums
        base_limits["per_minute"] = max(base_limits["per_minute"], 1)
        base_limits["per_hour"] = max(base_limits["per_hour"], 60)
        base_limits["per_day"] = max(base_limits["per_day"], 1440)
        
        return base_limits
    
    def _get_next_month_start(self, current_time: datetime) -> datetime:
        """Get the start of next month."""
        if current_time.month == 12:
            return current_time.replace(year=current_time.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            return current_time.replace(month=current_time.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0)
    
    async def get_user_rate_limit_status(self, user: User, plan: Plan) -> dict:
        """Get current rate limit status for a user."""
        now = datetime.utcnow()
        
        # Get current counts
        minute_key = f"rate_limit:{user.id}:minute:{now.strftime('%Y%m%d%H%M')}"
        hour_key = f"rate_limit:{user.id}:hour:{now.strftime('%Y%m%d%H')}"
        day_key = f"rate_limit:{user.id}:day:{now.strftime('%Y%m%d')}"
        month_key = f"rate_limit:{user.id}:month:{now.strftime('%Y%m')}"
        concurrent_key = f"concurrent:{user.id}"
        
        minute_count = int(await self.redis.get(minute_key) or "0")
        hour_count = int(await self.redis.get(hour_key) or "0")
        day_count = int(await self.redis.get(day_key) or "0")
        month_count = int(await self.redis.get(month_key) or "0")
        concurrent_count = int(await self.redis.get(concurrent_key) or "0")
        
        limits = self._get_plan_limits(plan)
        
        return {
            "current_usage": {
                "per_minute": minute_count,
                "per_hour": hour_count,
                "per_day": day_count,
                "per_month": month_count,
                "concurrent": concurrent_count
            },
            "limits": {
                "per_minute": limits["per_minute"],
                "per_hour": limits["per_hour"],
                "per_day": limits["per_day"],
                "per_month": limits["per_month"],
                "concurrent": plan.concurrent_requests
            },
            "remaining": {
                "per_minute": max(0, limits["per_minute"] - minute_count),
                "per_hour": max(0, limits["per_hour"] - hour_count),
                "per_day": max(0, limits["per_day"] - day_count),
                "per_month": max(0, limits["per_month"] - month_count),
                "concurrent": max(0, plan.concurrent_requests - concurrent_count)
            },
            "reset_times": {
                "minute": int((now + timedelta(minutes=1)).replace(second=0, microsecond=0).timestamp()),
                "hour": int((now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0).timestamp()),
                "day": int((now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0).timestamp()),
                "month": int(self._get_next_month_start(now).timestamp())
            }
        }
