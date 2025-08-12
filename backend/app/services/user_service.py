from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from datetime import datetime, timedelta
from typing import List, Optional
from app.models.user import User, Plan, Subscription, UsageCounter
from app.schemas.user import (
    UserUpdateRequest, UserProfileUpdate, SubscribeRequest,
    UsageStatsResponse, AdminUserUpdate
)
from app.core.security import get_password_hash
import json


class UserService:
    def __init__(self, db: Session):
        self.db = db

    def update_user_profile(self, user: User, update_data: UserProfileUpdate) -> User:
        """Update user profile information."""
        update_dict = update_data.dict(exclude_unset=True)
        
        # Check if email is being changed and if it's already taken
        if "email" in update_dict and update_dict["email"] != user.email:
            existing_user = self.db.query(User).filter(
                User.email == update_dict["email"],
                User.id != user.id
            ).first()
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered"
                )
        
        # Update user fields
        for field, value in update_dict.items():
            setattr(user, field, value)
        
        user.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(user)
        
        return user

    def deactivate_user(self, user: User, reason: Optional[str] = None) -> User:
        """Deactivate user account."""
        user.is_active = False
        user.updated_at = datetime.utcnow()
        
        # Optionally log the reason (could be stored in a separate table)
        # For now, we'll just set the user as inactive
        
        self.db.commit()
        self.db.refresh(user)
        
        return user

    def get_user_subscription(self, user_id: int) -> Optional[Subscription]:
        """Get active subscription for a user."""
        return self.db.query(Subscription).filter(
            Subscription.user_id == user_id,
            Subscription.status == "active",
            Subscription.current_period_end > datetime.utcnow()
        ).first()

    def subscribe_user_to_plan(self, user: User, subscribe_request: SubscribeRequest) -> Subscription:
        """Subscribe user to a plan."""
        # Check if plan exists and is active
        plan = self.db.query(Plan).filter(
            Plan.id == subscribe_request.plan_id,
            Plan.is_active == True
        ).first()
        
        if not plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Plan not found or inactive"
            )
        
        # Check if user already has an active subscription
        existing_subscription = self.get_user_subscription(user.id)
        if existing_subscription:
            # Deactivate existing subscription
            existing_subscription.status = "cancelled"
            existing_subscription.updated_at = datetime.utcnow()
        
        # Calculate period dates
        current_period_start = datetime.utcnow()
        if subscribe_request.billing_cycle == "yearly":
            current_period_end = current_period_start + timedelta(days=365)
        else:  # monthly
            current_period_end = current_period_start + timedelta(days=30)
        
        # Create new subscription
        subscription = Subscription(
            user_id=user.id,
            plan_id=plan.id,
            status="active",
            billing_cycle=subscribe_request.billing_cycle,
            current_period_start=current_period_start,
            current_period_end=current_period_end
        )
        
        self.db.add(subscription)
        
        # Create or reset usage counter
        usage_counter = self.db.query(UsageCounter).filter(
            UsageCounter.user_id == user.id
        ).first()
        
        if usage_counter:
            usage_counter.period_start = current_period_start
            usage_counter.period_end = current_period_end
            usage_counter.requests_count = 0
            usage_counter.last_reset = datetime.utcnow()
            usage_counter.updated_at = datetime.utcnow()
        else:
            usage_counter = UsageCounter(
                user_id=user.id,
                period_start=current_period_start,
                period_end=current_period_end,
                requests_count=0
            )
            self.db.add(usage_counter)
        
        self.db.commit()
        self.db.refresh(subscription)
        
        return subscription

    def get_usage_stats(self, user: User) -> UsageStatsResponse:
        """Get usage statistics for a user."""
        subscription = self.get_user_subscription(user.id)
        
        if not subscription:
            # Default to Free plan if no subscription
            free_plan = self.db.query(Plan).filter(Plan.name == "Free").first()
            if not free_plan:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Free plan not found"
                )
            
            # Create default usage stats
            current_time = datetime.utcnow()
            return UsageStatsResponse(
                user_id=user.id,
                current_period_start=current_time.replace(day=1),
                current_period_end=current_time.replace(day=1) + timedelta(days=30),
                requests_used=0,
                requests_limit=free_plan.requests_per_month,
                requests_remaining=free_plan.requests_per_month,
                usage_percentage=0.0,
                plan_name=free_plan.name
            )
        
        # Get usage counter
        usage_counter = self.db.query(UsageCounter).filter(
            UsageCounter.user_id == user.id
        ).first()
        
        requests_used = usage_counter.requests_count if usage_counter else 0
        requests_limit = subscription.plan.requests_per_month
        requests_remaining = max(0, requests_limit - requests_used)
        usage_percentage = (requests_used / requests_limit * 100) if requests_limit > 0 else 0
        
        return UsageStatsResponse(
            user_id=user.id,
            current_period_start=subscription.current_period_start,
            current_period_end=subscription.current_period_end,
            requests_used=requests_used,
            requests_limit=requests_limit,
            requests_remaining=requests_remaining,
            usage_percentage=round(usage_percentage, 2),
            plan_name=subscription.plan.name
        )

    def get_all_plans(self) -> List[Plan]:
        """Get all active plans."""
        plans = self.db.query(Plan).filter(Plan.is_active == True).all()
        
        # Parse features JSON for each plan
        for plan in plans:
            if plan.features:
                try:
                    plan.features = json.loads(plan.features)
                except json.JSONDecodeError:
                    plan.features = []
            else:
                plan.features = []
        
        return plans
    
    def get_plan_by_id(self, plan_id: int) -> Optional[Plan]:
        """Get plan by id."""
        plan = self.db.query(Plan).filter(Plan.id == plan_id).first()
        if plan and plan.features:
            try:
                plan.features = json.loads(plan.features)
            except json.JSONDecodeError:
                plan.features = []
        return plan
