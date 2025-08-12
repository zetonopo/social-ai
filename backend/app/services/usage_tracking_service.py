from datetime import datetime, timedelta
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from app.models.user import User, UsageCounter, Subscription, Plan
from app.core.redis_client import RedisClient
from app.services.cache_service import CacheService
import asyncio
import json


class UsageTrackingService:
    def __init__(self, db: Session, redis_client: RedisClient):
        self.db = db
        self.redis = redis_client
        self.cache_service = CacheService(redis_client)
    
    async def track_api_request(self, user_id: int, endpoint: str, method: str, status_code: int, response_time_ms: float):
        """Track an API request in Redis for real-time processing."""
        timestamp = datetime.utcnow()
        
        # Create request log entry
        request_log = {
            "user_id": user_id,
            "endpoint": endpoint,
            "method": method,
            "status_code": status_code,
            "response_time_ms": response_time_ms,
            "timestamp": timestamp.isoformat()
        }
        
        # Store in Redis list for batch processing
        request_key = f"api_requests:{timestamp.strftime('%Y%m%d%H')}"  # Group by hour
        await self.redis.lpush(request_key, json.dumps(request_log, default=str))
        await self.redis.expire(request_key, 7200)  # Keep for 2 hours
        
        # Update real-time counters
        await self._update_realtime_counters(user_id, timestamp)
    
    async def _update_realtime_counters(self, user_id: int, timestamp: datetime):
        """Update real-time usage counters in Redis."""
        # Daily counter
        day_key = f"usage_daily:{user_id}:{timestamp.strftime('%Y%m%d')}"
        await self.redis.incr(day_key)
        await self.redis.expire(day_key, 86400 * 2)  # Keep for 2 days
        
        # Monthly counter
        month_key = f"usage_monthly:{user_id}:{timestamp.strftime('%Y%m')}"
        await self.redis.incr(month_key)
        await self.redis.expire(month_key, 86400 * 35)  # Keep for 35 days
        
        # Hourly counter for analytics
        hour_key = f"usage_hourly:{user_id}:{timestamp.strftime('%Y%m%d%H')}"
        await self.redis.incr(hour_key)
        await self.redis.expire(hour_key, 86400 * 7)  # Keep for 7 days
    
    async def persist_usage_data(self):
        """Persist usage data from Redis to PostgreSQL (run periodically)."""
        now = datetime.utcnow()
        
        # Process data from the previous hour
        prev_hour = now - timedelta(hours=1)
        request_key = f"api_requests:{prev_hour.strftime('%Y%m%d%H')}"
        
        # Get all requests from the previous hour
        requests_json = []
        while True:
            request_data = await self.redis.rpop(request_key)
            if not request_data:
                break
            requests_json.append(request_data)
        
        if not requests_json:
            return
        
        # Group requests by user
        user_requests = {}
        for request_json in requests_json:
            try:
                request_data = json.loads(request_json)
                user_id = request_data["user_id"]
                if user_id not in user_requests:
                    user_requests[user_id] = []
                user_requests[user_id].append(request_data)
            except json.JSONDecodeError:
                continue
        
        # Update database usage counters
        for user_id, requests in user_requests.items():
            await self._update_database_usage(user_id, requests, prev_hour)
    
    async def _update_database_usage(self, user_id: int, requests: List[dict], hour: datetime):
        """Update database usage counters for a user."""
        # Get or create usage counter for current billing period
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return
        
        # Get user's current subscription to determine billing period
        subscription = self.db.query(Subscription).filter(
            Subscription.user_id == user_id,
            Subscription.status == "active",
            Subscription.current_period_end > datetime.utcnow()
        ).first()
        
        if subscription:
            period_start = subscription.current_period_start
            period_end = subscription.current_period_end
        else:
            # Default to monthly periods for free users
            period_start = hour.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if period_start.month == 12:
                period_end = period_start.replace(year=period_start.year + 1, month=1)
            else:
                period_end = period_start.replace(month=period_start.month + 1)
        
        # Get or create usage counter
        usage_counter = self.db.query(UsageCounter).filter(
            UsageCounter.user_id == user_id,
            UsageCounter.period_start <= hour,
            UsageCounter.period_end > hour
        ).first()
        
        if not usage_counter:
            usage_counter = UsageCounter(
                user_id=user_id,
                period_start=period_start,
                period_end=period_end,
                requests_count=0
            )
            self.db.add(usage_counter)
        
        # Count successful requests (2xx status codes)
        successful_requests = len([r for r in requests if 200 <= r.get("status_code", 0) < 300])
        
        # Update counter
        usage_counter.requests_count += successful_requests
        usage_counter.updated_at = datetime.utcnow()
        
        self.db.commit()
    
    async def get_user_usage_analytics(self, user_id: int, days: int = 30) -> Dict:
        """Get detailed usage analytics for a user."""
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Get daily usage from Redis
        daily_usage = {}
        for i in range(days):
            date = start_date + timedelta(days=i)
            day_key = f"usage_daily:{user_id}:{date.strftime('%Y%m%d')}"
            count = await self.redis.get(day_key) or "0"
            daily_usage[date.strftime('%Y-%m-%d')] = int(count)
        
        # Get hourly usage for today from Redis
        today = end_date.strftime('%Y%m%d')
        hourly_usage = {}
        for hour in range(24):
            hour_key = f"usage_hourly:{user_id}:{today}{hour:02d}"
            count = await self.redis.get(hour_key) or "0"
            hourly_usage[f"{hour:02d}:00"] = int(count)
        
        # Get monthly totals from database
        monthly_totals = self.db.query(
            func.date_trunc('month', UsageCounter.period_start).label('month'),
            func.sum(UsageCounter.requests_count).label('total_requests')
        ).filter(
            UsageCounter.user_id == user_id,
            UsageCounter.period_start >= start_date
        ).group_by(
            func.date_trunc('month', UsageCounter.period_start)
        ).all()
        
        monthly_data = {}
        for month, total in monthly_totals:
            monthly_data[month.strftime('%Y-%m')] = total
        
        return {
            "daily_usage": daily_usage,
            "hourly_usage_today": hourly_usage,
            "monthly_totals": monthly_data,
            "total_requests_period": sum(daily_usage.values())
        }
    
    async def get_system_usage_analytics(self, days: int = 30) -> Dict:
        """Get system-wide usage analytics."""
        # Check cache first
        cached_stats = await self.cache_service.get_cached_system_stats()
        if cached_stats and "analytics" in cached_stats:
            return cached_stats["analytics"]
        
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Get total requests by day
        daily_totals = self.db.query(
            func.date(UsageCounter.updated_at).label('date'),
            func.sum(UsageCounter.requests_count).label('total_requests')
        ).filter(
            UsageCounter.updated_at >= start_date
        ).group_by(
            func.date(UsageCounter.updated_at)
        ).all()
        
        daily_data = {}
        for date, total in daily_totals:
            daily_data[date.strftime('%Y-%m-%d')] = total or 0
        
        # Get usage by plan
        plan_usage = self.db.query(
            Plan.name,
            func.sum(UsageCounter.requests_count).label('total_requests')
        ).join(
            Subscription, Subscription.plan_id == Plan.id
        ).join(
            UsageCounter, UsageCounter.user_id == Subscription.user_id
        ).filter(
            UsageCounter.updated_at >= start_date,
            Subscription.status == "active"
        ).group_by(Plan.name).all()
        
        plan_data = {}
        for plan_name, total in plan_usage:
            plan_data[plan_name] = total or 0
        
        # Get top users by usage
        top_users = self.db.query(
            User.email,
            func.sum(UsageCounter.requests_count).label('total_requests')
        ).join(
            UsageCounter, UsageCounter.user_id == User.id
        ).filter(
            UsageCounter.updated_at >= start_date
        ).group_by(User.id, User.email).order_by(
            func.sum(UsageCounter.requests_count).desc()
        ).limit(10).all()
        
        top_users_data = []
        for email, total in top_users:
            top_users_data.append({
                "email": email,
                "total_requests": total or 0
            })
        
        analytics = {
            "daily_totals": daily_data,
            "usage_by_plan": plan_data,
            "top_users": top_users_data,
            "total_requests": sum(daily_data.values()),
            "period_days": days
        }
        
        # Cache the results
        await self.cache_service.cache_system_stats({"analytics": analytics}, 1800)  # 30 minutes
        
        return analytics
    
    async def reset_user_usage(self, user_id: int):
        """Reset usage counters for a user (admin function)."""
        # Get current usage counter
        usage_counter = self.db.query(UsageCounter).filter(
            UsageCounter.user_id == user_id,
            UsageCounter.period_end > datetime.utcnow()
        ).first()
        
        if usage_counter:
            usage_counter.requests_count = 0
            usage_counter.last_reset = datetime.utcnow()
            usage_counter.updated_at = datetime.utcnow()
            self.db.commit()
        
        # Clear Redis counters
        now = datetime.utcnow()
        keys_to_clear = [
            f"usage_daily:{user_id}:{now.strftime('%Y%m%d')}",
            f"usage_monthly:{user_id}:{now.strftime('%Y%m')}",
            f"rate_limit:{user_id}:*"
        ]
        
        for key in keys_to_clear:
            if "*" not in key:
                await self.redis.delete(key)
        
        # Invalidate cache
        await self.cache_service.invalidate_user_cache(user_id)
    
    async def get_user_usage_summary(self, user_id: int) -> Dict:
        """Get current usage summary for a user (for dashboard)."""
        try:
            # Get user's current subscription
            subscription = self.db.query(Subscription).filter(
                Subscription.user_id == user_id,
                Subscription.status == 'active'
            ).first()
            
            if not subscription:
                return {
                    "current_usage": 0,
                    "limit": 100,  # Default free limit
                    "remaining": 100,
                    "percentage": 0.0,
                    "reset_date": None
                }
            
            # Get plan details
            plan = self.db.query(Plan).filter(Plan.id == subscription.plan_id).first()
            if not plan:
                return {
                    "current_usage": 0,
                    "limit": 100,
                    "remaining": 100,
                    "percentage": 0.0,
                    "reset_date": None
                }
            
            # Get usage counter for current period
            usage_counter = self.db.query(UsageCounter).filter(
                UsageCounter.user_id == user_id,
                UsageCounter.period_start <= datetime.utcnow(),
                UsageCounter.period_end >= datetime.utcnow()
            ).first()
            
            current_usage = usage_counter.requests_count if usage_counter else 0
            limit = plan.requests_per_month
            remaining = max(0, limit - current_usage)
            percentage = (current_usage / limit * 100) if limit > 0 else 0
            
            return {
                "current_usage": current_usage,
                "limit": limit,
                "remaining": remaining,
                "percentage": round(percentage, 1),
                "reset_date": subscription.current_period_end.isoformat() if subscription.current_period_end else None
            }
            
        except Exception as e:
            # Return default values on error
            return {
                "current_usage": 0,
                "limit": 100,
                "remaining": 100,
                "percentage": 0.0,
                "reset_date": None
            }
