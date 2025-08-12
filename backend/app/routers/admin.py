from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.core.auth import get_current_superuser
from app.schemas.user import (
    AdminUserResponse, AdminUserUpdate, SystemUsageStats,
    SubscriptionResponse, PlanResponse
)
from app.services.admin_service import AdminService
from app.services.user_service import UserService
from app.models.user import User
import json

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/users", response_model=List[AdminUserResponse])
async def get_all_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db)
):
    """Get all users (admin only)."""
    admin_service = AdminService(db)
    user_service = UserService(db)
    
    users = admin_service.get_all_users(skip=skip, limit=limit)
    
    # Build response with subscription and usage info
    user_responses = []
    for user in users:
        subscription = user_service.get_user_subscription(user.id)
        usage_stats = None
        
        try:
            usage_stats = user_service.get_usage_stats(user)
        except:
            pass  # If there's an error getting usage stats, continue without it
        
        user_response = AdminUserResponse(
            id=user.id,
            email=user.email,
            is_active=user.is_active,
            is_superuser=user.is_superuser,
            created_at=user.created_at,
            updated_at=user.updated_at,
            subscription=subscription,
            usage_stats=usage_stats
        )
        user_responses.append(user_response)
    
    return user_responses


@router.get("/users/{user_id}", response_model=AdminUserResponse)
async def get_user_by_id(
    user_id: int,
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db)
):
    """Get user by ID (admin only)."""
    admin_service = AdminService(db)
    user_service = UserService(db)
    
    user = admin_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    subscription = user_service.get_user_subscription(user.id)
    usage_stats = None
    
    try:
        usage_stats = user_service.get_usage_stats(user)
    except:
        pass
    
    return AdminUserResponse(
        id=user.id,
        email=user.email,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        created_at=user.created_at,
        updated_at=user.updated_at,
        subscription=subscription,
        usage_stats=usage_stats
    )


@router.patch("/users/{user_id}", response_model=AdminUserResponse)
async def update_user(
    user_id: int,
    update_data: AdminUserUpdate,
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db)
):
    """Update user (admin only)."""
    admin_service = AdminService(db)
    user_service = UserService(db)
    
    updated_user = admin_service.update_user(user_id, update_data)
    
    subscription = user_service.get_user_subscription(updated_user.id)
    usage_stats = None
    
    try:
        usage_stats = user_service.get_usage_stats(updated_user)
    except:
        pass
    
    return AdminUserResponse(
        id=updated_user.id,
        email=updated_user.email,
        is_active=updated_user.is_active,
        is_superuser=updated_user.is_superuser,
        created_at=updated_user.created_at,
        updated_at=updated_user.updated_at,
        subscription=subscription,
        usage_stats=usage_stats
    )


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db)
):
    """Delete user (admin only)."""
    admin_service = AdminService(db)
    success = admin_service.delete_user(user_id)
    
    if success:
        return {"message": "User deleted successfully"}
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete user"
        )


@router.get("/subscriptions", response_model=List[SubscriptionResponse])
async def get_all_subscriptions(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db)
):
    """Get all subscriptions (admin only)."""
    admin_service = AdminService(db)
    subscriptions = admin_service.get_all_subscriptions(skip=skip, limit=limit)
    return subscriptions


@router.post("/subscriptions/{subscription_id}/cancel")
async def cancel_subscription(
    subscription_id: int,
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db)
):
    """Cancel subscription (admin only)."""
    admin_service = AdminService(db)
    subscription = admin_service.cancel_subscription(subscription_id)
    return {"message": f"Subscription {subscription_id} cancelled successfully"}


@router.get("/usage", response_model=SystemUsageStats)
async def get_system_usage_stats(
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db)
):
    """Get system-wide usage statistics (admin only)."""
    admin_service = AdminService(db)
    stats = admin_service.get_system_usage_stats()
    return stats


@router.post("/plans", response_model=PlanResponse)
async def create_plan(
    plan_data: dict,
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db)
):
    """Create a new plan (admin only)."""
    admin_service = AdminService(db)
    
    # Ensure features is properly formatted
    if "features" in plan_data and isinstance(plan_data["features"], list):
        plan_data["features"] = json.dumps(plan_data["features"])
    
    plan = admin_service.create_plan(plan_data)
    
    # Parse features back to list for response
    features = []
    if plan.features:
        try:
            features = json.loads(plan.features)
        except:
            features = []
    
    return PlanResponse(
        id=plan.id,
        name=plan.name,
        description=plan.description,
        monthly_price=plan.monthly_price,
        yearly_price=plan.yearly_price,
        requests_per_month=plan.requests_per_month,
        concurrent_requests=plan.concurrent_requests,
        features=features,
        is_active=plan.is_active,
        created_at=plan.created_at
    )


@router.patch("/plans/{plan_id}", response_model=PlanResponse)
async def update_plan(
    plan_id: int,
    plan_data: dict,
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db)
):
    """Update a plan (admin only)."""
    admin_service = AdminService(db)
    
    # Ensure features is properly formatted
    if "features" in plan_data and isinstance(plan_data["features"], list):
        plan_data["features"] = json.dumps(plan_data["features"])
    
    plan = admin_service.update_plan(plan_id, plan_data)
    
    # Parse features back to list for response
    features = []
    if plan.features:
        try:
            features = json.loads(plan.features)
        except:
            features = []
    
    return PlanResponse(
        id=plan.id,
        name=plan.name,
        description=plan.description,
        monthly_price=plan.monthly_price,
        yearly_price=plan.yearly_price,
        requests_per_month=plan.requests_per_month,
        concurrent_requests=plan.concurrent_requests,
        features=features,
        is_active=plan.is_active,
        created_at=plan.created_at
    )
