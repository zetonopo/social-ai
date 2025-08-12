from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from fastapi import HTTPException, status
from datetime import datetime, timedelta
from typing import List, Optional
from app.models.user import User, Plan, Subscription, UsageCounter
from app.schemas.user import AdminUserUpdate, SystemUsageStats
from app.services.user_service import UserService


class AdminService:
    def __init__(self, db: Session):
        self.db = db
        self.user_service = UserService(db)

    def get_all_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        """Get all users with pagination."""
        return self.db.query(User).offset(skip).limit(limit).all()

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        return self.db.query(User).filter(User.id == user_id).first()

    def update_user(self, user_id: int, update_data: AdminUserUpdate) -> User:
        """Update user by admin."""
        user = self.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
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

    def delete_user(self, user_id: int) -> bool:
        """Delete user (soft delete by deactivating)."""
        user = self.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Prevent deletion of superusers
        if user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot delete superuser"
            )
        
        user.is_active = False
        user.updated_at = datetime.utcnow()
        self.db.commit()
        
        return True

    def get_all_subscriptions(self, skip: int = 0, limit: int = 100) -> List[Subscription]:
        """Get all subscriptions with pagination."""
        return self.db.query(Subscription).offset(skip).limit(limit).all()

    def cancel_subscription(self, subscription_id: int) -> Subscription:
        """Cancel a subscription."""
        subscription = self.db.query(Subscription).filter(
            Subscription.id == subscription_id
        ).first()
        
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subscription not found"
            )
        
        subscription.status = "cancelled"
        subscription.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(subscription)
        
        return subscription

    def get_system_usage_stats(self) -> SystemUsageStats:
        """Get system-wide usage statistics."""
        # Total users
        total_users = self.db.query(func.count(User.id)).scalar()
        
        # Active users
        active_users = self.db.query(func.count(User.id)).filter(
            User.is_active == True
        ).scalar()
        
        # Today's date for filtering
        today = datetime.utcnow().date()
        current_month_start = datetime.utcnow().replace(day=1)
        
        # Total requests today (assuming we track this in usage_counters)
        # For now, we'll simulate this data
        total_requests_today = 0  # Would need request logging to get actual data
        
        # Total requests this month
        total_requests_month = self.db.query(func.sum(UsageCounter.requests_count)).filter(
            UsageCounter.period_start >= current_month_start
        ).scalar() or 0
        
        # Users by plan
        users_by_plan = {}
        plans = self.db.query(Plan).all()
        
        for plan in plans:
            # Count active subscriptions for each plan
            count = self.db.query(func.count(Subscription.id)).filter(
                Subscription.plan_id == plan.id,
                Subscription.status == "active",
                Subscription.current_period_end > datetime.utcnow()
            ).scalar()
            users_by_plan[plan.name] = count
        
        # Users without active subscription (on free plan)
        subscribed_users = self.db.query(func.count(Subscription.user_id.distinct())).filter(
            Subscription.status == "active",
            Subscription.current_period_end > datetime.utcnow()
        ).scalar()
        users_by_plan["Free"] = total_users - subscribed_users
        
        # Revenue this month (simplified calculation)
        revenue_month = 0.0
        monthly_subscriptions = self.db.query(Subscription).filter(
            Subscription.status == "active",
            Subscription.billing_cycle == "monthly",
            Subscription.current_period_start >= current_month_start
        ).all()
        
        yearly_subscriptions = self.db.query(Subscription).filter(
            Subscription.status == "active",
            Subscription.billing_cycle == "yearly",
            Subscription.current_period_start >= current_month_start
        ).all()
        
        for sub in monthly_subscriptions:
            revenue_month += sub.plan.monthly_price
        
        for sub in yearly_subscriptions:
            revenue_month += sub.plan.yearly_price / 12  # Monthly equivalent
        
        return SystemUsageStats(
            total_users=total_users,
            active_users=active_users,
            total_requests_today=total_requests_today,
            total_requests_month=int(total_requests_month),
            users_by_plan=users_by_plan,
            revenue_month=round(revenue_month, 2)
        )

    def create_plan(self, plan_data: dict) -> Plan:
        """Create a new plan."""
        plan = Plan(**plan_data)
        self.db.add(plan)
        self.db.commit()
        self.db.refresh(plan)
        return plan

    def update_plan(self, plan_id: int, plan_data: dict) -> Plan:
        """Update an existing plan."""
        plan = self.db.query(Plan).filter(Plan.id == plan_id).first()
        if not plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Plan not found"
            )
        
        for field, value in plan_data.items():
            if hasattr(plan, field):
                setattr(plan, field, value)
        
        plan.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(plan)
        
        return plan
