from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class UserStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class UserUpdateRequest(BaseModel):
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None


class UserProfileUpdate(BaseModel):
    email: Optional[EmailStr] = None


class UserDeactivateRequest(BaseModel):
    reason: Optional[str] = None


class PlanResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    monthly_price: float
    yearly_price: Optional[float] = None
    requests_per_month: int
    concurrent_requests: int
    features: List[str] = []
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class SubscriptionResponse(BaseModel):
    id: int
    user_id: int
    plan_id: int
    plan: PlanResponse
    status: str
    billing_cycle: str
    current_period_start: datetime
    current_period_end: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class SubscribeRequest(BaseModel):
    plan_id: int
    billing_cycle: str = Field(..., pattern="^(monthly|yearly)$")


class UsageStatsResponse(BaseModel):
    user_id: int
    current_period_start: datetime
    current_period_end: datetime
    requests_used: int
    requests_limit: int
    requests_remaining: int
    usage_percentage: float
    plan_name: str


class AdminUserResponse(BaseModel):
    id: int
    email: str
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    subscription: Optional[SubscriptionResponse] = None
    usage_stats: Optional[UsageStatsResponse] = None

    class Config:
        from_attributes = True


class AdminUserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None


class SystemUsageStats(BaseModel):
    total_users: int
    active_users: int
    total_requests_today: int
    total_requests_month: int
    users_by_plan: dict
    revenue_month: float
