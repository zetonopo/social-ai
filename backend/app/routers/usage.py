from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Dict, Optional
from datetime import datetime
from app.core.database import get_db
from app.core.security import get_current_user, require_admin
from app.models.user import User
from app.services.usage_tracking_service import UsageTrackingService
from app.core.redis_client import RedisClient

router = APIRouter(prefix="/usage", tags=["usage"])


def get_redis_client() -> RedisClient:
    """Get Redis client from app state (placeholder for dependency injection)."""
    # This would typically be injected via FastAPI dependency
    # For now, we'll create a new instance
    return RedisClient()


@router.get("", response_model=Dict)
@router.get("/", response_model=Dict)
async def get_user_usage(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's usage statistics."""
    try:
        redis_client = get_redis_client()
        usage_service = UsageTrackingService(db, redis_client)
        
        # Get current usage summary for dashboard
        usage_summary = await usage_service.get_user_usage_summary(current_user.id)
        
        return {
            "data": usage_summary,
            "message": "Usage data retrieved successfully",
            "status": "success"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve usage statistics: {str(e)}"
        )


@router.get("/analytics", response_model=Dict)
async def get_user_usage_analytics(
    days: int = Query(default=30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get usage analytics for the current user."""
    try:
        redis_client = get_redis_client()
        usage_service = UsageTrackingService(db, redis_client)
        
        analytics = await usage_service.get_user_usage_analytics(
            user_id=current_user.id,
            days=days
        )
        
        return {
            "success": True,
            "data": analytics
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve usage analytics: {str(e)}"
        )


@router.get("/current", response_model=Dict)
async def get_current_usage(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current usage status for the user."""
    try:
        redis_client = get_redis_client()
        usage_service = UsageTrackingService(db, redis_client)
        
        # Get today's usage
        today = datetime.utcnow()
        day_key = f"usage_daily:{current_user.id}:{today.strftime('%Y%m%d')}"
        daily_usage = await redis_client.get(day_key) or "0"
        
        # Get monthly usage
        month_key = f"usage_monthly:{current_user.id}:{today.strftime('%Y%m')}"
        monthly_usage = await redis_client.get(month_key) or "0"
        
        # Get user's plan limits
        from app.services.cache_service import CacheService
        cache_service = CacheService(redis_client)
        subscription = await cache_service.get_user_subscription(current_user.id)
        
        plan_limits = {
            "daily_limit": subscription.get("plan", {}).get("daily_requests", 1000) if subscription else 100,
            "monthly_limit": subscription.get("plan", {}).get("monthly_requests", 30000) if subscription else 3000
        }
        
        return {
            "success": True,
            "data": {
                "user_id": current_user.id,
                "daily_usage": int(daily_usage),
                "monthly_usage": int(monthly_usage),
                "limits": plan_limits,
                "daily_remaining": max(0, plan_limits["daily_limit"] - int(daily_usage)),
                "monthly_remaining": max(0, plan_limits["monthly_limit"] - int(monthly_usage))
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve current usage: {str(e)}"
        )


@router.get("/rate-limit-status", response_model=Dict)
async def get_rate_limit_status(
    current_user: User = Depends(get_current_user)
):
    """Get current rate limit status for the user."""
    try:
        redis_client = get_redis_client()
        
        # Get rate limit status for different windows
        user_id = current_user.id
        now = datetime.utcnow()
        
        # Check different time windows
        windows = {
            "minute": f"rate_limit:{user_id}:minute:{now.strftime('%Y%m%d%H%M')}",
            "hour": f"rate_limit:{user_id}:hour:{now.strftime('%Y%m%d%H')}",
            "day": f"rate_limit:{user_id}:day:{now.strftime('%Y%m%d')}",
            "month": f"rate_limit:{user_id}:month:{now.strftime('%Y%m')}"
        }
        
        status_data = {}
        for window, key in windows.items():
            current_count = await redis_client.get(key) or "0"
            status_data[window] = {
                "current_requests": int(current_count),
                "window": window
            }
        
        # Get concurrent requests
        concurrent_key = f"concurrent:{user_id}"
        concurrent_count = await redis_client.get(concurrent_key) or "0"
        
        return {
            "success": True,
            "data": {
                "user_id": user_id,
                "rate_limits": status_data,
                "concurrent_requests": int(concurrent_count)
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve rate limit status: {str(e)}"
        )


# Admin endpoints
@router.get("/admin/analytics", response_model=Dict)
async def get_system_usage_analytics(
    days: int = Query(default=30, ge=1, le=365),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get system-wide usage analytics (admin only)."""
    try:
        redis_client = get_redis_client()
        usage_service = UsageTrackingService(db, redis_client)
        
        analytics = await usage_service.get_system_usage_analytics(days=days)
        
        return {
            "success": True,
            "data": analytics
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve system analytics: {str(e)}"
        )


@router.post("/admin/reset/{user_id}", response_model=Dict)
async def reset_user_usage(
    user_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Reset usage counters for a specific user (admin only)."""
    try:
        # Check if user exists
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        redis_client = get_redis_client()
        usage_service = UsageTrackingService(db, redis_client)
        
        await usage_service.reset_user_usage(user_id)
        
        return {
            "success": True,
            "message": f"Usage counters reset for user {user.email}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset user usage: {str(e)}"
        )


@router.post("/admin/persist", response_model=Dict)
async def persist_usage_data(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Manually trigger usage data persistence from Redis to PostgreSQL (admin only)."""
    try:
        redis_client = get_redis_client()
        usage_service = UsageTrackingService(db, redis_client)
        
        await usage_service.persist_usage_data()
        
        return {
            "success": True,
            "message": "Usage data persistence completed"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to persist usage data: {str(e)}"
        )
