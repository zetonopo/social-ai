from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict
from datetime import datetime
from app.core.database import get_db
from app.core.auth import get_current_active_user
from app.schemas.user import (
    UserProfileUpdate, UserDeactivateRequest, PlanResponse,
    SubscribeRequest, SubscriptionResponse, UsageStatsResponse,
    UserSettings, UserSettingsResponse
)
from app.schemas.auth import UserResponse
from app.services.user_service import UserService
from app.models.user import User
import json

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserResponse)
async def get_my_profile(
    current_user: User = Depends(get_current_active_user)
):
    """Get current user's profile."""
    return current_user


@router.get("/me/profile")
async def get_my_profile_with_subscription(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get current user's profile with subscription info."""
    user_service = UserService(db)
    
    # Get user's subscription
    subscription = user_service.get_user_subscription(current_user.id)
    plan = None
    
    if subscription:
        plan = user_service.get_plan_by_id(subscription.plan_id)
    
    return {
        "id": current_user.id,
        "email": current_user.email,
        "is_active": current_user.is_active,
        "is_superuser": current_user.is_superuser,
        "created_at": current_user.created_at,
        "updated_at": current_user.updated_at,
        "subscription": {
            "plan_id": subscription.plan_id if subscription else None,
            "plan_name": plan.name if plan else None,
            "status": subscription.status if subscription else None,
            "current_period_end": subscription.current_period_end if subscription else None
        } if subscription else None
    }


@router.patch("/me", response_model=UserResponse)
async def update_my_profile(
    update_data: UserProfileUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update current user's profile."""
    user_service = UserService(db)
    updated_user = user_service.update_user_profile(current_user, update_data)
    return updated_user


@router.patch("/me/password")
async def change_my_password(
    password_data: dict,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Change current user's password."""
    from app.core.security import verify_password, get_password_hash
    
    current_password = password_data.get("current_password")
    new_password = password_data.get("new_password")
    
    if not current_password or not new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password and new password are required"
        )
    
    # Verify current password
    if not verify_password(current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Update password
    current_user.password_hash = get_password_hash(new_password)
    current_user.updated_at = datetime.utcnow()
    db.commit()
    
    return {"message": "Password changed successfully"}


@router.post("/me/deactivate")
async def deactivate_my_account(
    deactivate_request: UserDeactivateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Deactivate current user's account."""
    user_service = UserService(db)
    user_service.deactivate_user(current_user, deactivate_request.reason)
    return {"message": "Account deactivated successfully"}


@router.get("/plans", response_model=Dict)
async def get_available_plans(
    db: Session = Depends(get_db)
):
    """Get all available subscription plans."""
    user_service = UserService(db)
    plans = user_service.get_all_plans()
    
    # Convert plans to response format
    plan_responses = []
    for plan in plans:
        plan_dict = {
            "id": plan.id,
            "name": plan.name,
            "description": plan.description,
            "monthly_price": plan.monthly_price,
            "yearly_price": plan.yearly_price,
            "requests_per_month": plan.requests_per_month,
            "concurrent_requests": plan.concurrent_requests,
            "features": plan.features if isinstance(plan.features, list) else [],
            "is_active": plan.is_active,
            "created_at": plan.created_at
        }
        plan_responses.append(plan_dict)
    
    return {
        "data": plan_responses,
        "message": "Plans retrieved successfully",
        "status": "success"
    }


@router.post("/subscribe", response_model=SubscriptionResponse)
async def subscribe_to_plan(
    subscribe_request: SubscribeRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Subscribe current user to a plan."""
    user_service = UserService(db)
    subscription = user_service.subscribe_user_to_plan(current_user, subscribe_request)
    return subscription


@router.get("/my-subscription", response_model=SubscriptionResponse)
async def get_my_subscription(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get current user's active subscription."""
    user_service = UserService(db)
    subscription = user_service.get_user_subscription(current_user.id)
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active subscription found"
        )
    
    return subscription


@router.get("/usage", response_model=UsageStatsResponse)
async def get_my_usage_stats(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get current user's usage statistics."""
    user_service = UserService(db)
    usage_stats = user_service.get_usage_stats(current_user)
    return usage_stats


@router.post("/cancel-subscription")
async def cancel_my_subscription(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Cancel current user's subscription."""
    user_service = UserService(db)
    subscription = user_service.get_user_subscription(current_user.id)
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active subscription found"
        )
    
    subscription.status = "cancelled"
    subscription.updated_at = db.query(User).filter(User.id == current_user.id).first().updated_at
    db.commit()
    
    return {"message": "Subscription cancelled successfully"}


@router.get("/settings", response_model=UserSettingsResponse)
async def get_my_settings(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get current user's settings."""
    from app.models.user import UserSettings as UserSettingsModel
    
    user_settings = db.query(UserSettingsModel).filter(
        UserSettingsModel.user_id == current_user.id
    ).first()
    
    if not user_settings:
        # Create default settings if not exists
        user_settings = UserSettingsModel(
            user_id=current_user.id,
            email_notifications=True,
            push_notifications=True,
            marketing_emails=False,
            profile_visibility="public",
            show_activity=True,
            language="en",
            theme="light",
            timezone="UTC"
        )
        db.add(user_settings)
        db.commit()
        db.refresh(user_settings)
    
    return {
        "notifications": {
            "email_notifications": user_settings.email_notifications,
            "push_notifications": user_settings.push_notifications,
            "marketing_emails": user_settings.marketing_emails,
        },
        "privacy": {
            "profile_visibility": user_settings.profile_visibility,
            "show_activity": user_settings.show_activity,
        },
        "preferences": {
            "language": user_settings.language,
            "theme": user_settings.theme,
            "timezone": user_settings.timezone,
        }
    }


@router.put("/settings")
async def update_my_settings(
    settings: UserSettings,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update current user's settings."""
    from app.models.user import UserSettings as UserSettingsModel
    
    user_settings = db.query(UserSettingsModel).filter(
        UserSettingsModel.user_id == current_user.id
    ).first()
    
    if not user_settings:
        # Create new settings if not exists
        user_settings = UserSettingsModel(
            user_id=current_user.id,
            email_notifications=settings.notifications.email_notifications,
            push_notifications=settings.notifications.push_notifications,
            marketing_emails=settings.notifications.marketing_emails,
            profile_visibility=settings.privacy.profile_visibility,
            show_activity=settings.privacy.show_activity,
            language=settings.preferences.language,
            theme=settings.preferences.theme,
            timezone=settings.preferences.timezone
        )
        db.add(user_settings)
    else:
        # Update existing settings
        user_settings.email_notifications = settings.notifications.email_notifications
        user_settings.push_notifications = settings.notifications.push_notifications
        user_settings.marketing_emails = settings.notifications.marketing_emails
        user_settings.profile_visibility = settings.privacy.profile_visibility
        user_settings.show_activity = settings.privacy.show_activity
        user_settings.language = settings.preferences.language
        user_settings.theme = settings.preferences.theme
        user_settings.timezone = settings.preferences.timezone
    
    db.commit()
    return {"message": "Settings updated successfully"}


@router.delete("/me")
async def delete_my_account(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete current user's account."""
    from app.models.user import UserSettings as UserSettingsModel
    
    # Delete user's settings first
    db.query(UserSettingsModel).filter(
        UserSettingsModel.user_id == current_user.id
    ).delete()
    
    # Delete user's refresh tokens
    from app.models.user import RefreshToken
    db.query(RefreshToken).filter(
        RefreshToken.user_id == current_user.id
    ).delete()
    
    # Delete user's subscriptions
    from app.models.user import Subscription
    db.query(Subscription).filter(
        Subscription.user_id == current_user.id
    ).delete()
    
    # Delete user's usage counters
    from app.models.user import UsageCounter
    db.query(UsageCounter).filter(
        UsageCounter.user_id == current_user.id
    ).delete()
    
    # Finally delete the user
    db.delete(current_user)
    db.commit()
    
    return {"message": "Account deleted successfully"}
