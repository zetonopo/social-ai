import uuid
from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.core.redis_client import redis_client
from app.services.rate_limit_service import RateLimitService
from app.services.user_service import UserService
from app.models.user import User
from app.core.security import verify_token
import time
import asyncio


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.rate_limit_service = RateLimitService(redis_client)
    
    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for certain paths
        skip_paths = [
            "/docs",
            "/redoc",
            "/openapi.json",
            "/health",
            "/auth/login",
            "/auth/register",
            "/auth/refresh",
            "/"
        ]
        
        if request.url.path in skip_paths or request.url.path.startswith("/static"):
            return await call_next(request)
        
        # Skip for OPTIONS requests
        if request.method == "OPTIONS":
            return await call_next(request)
        
        # Extract user from token
        user = await self._get_user_from_request(request)
        if not user:
            # If no valid user, allow request but log it
            return await call_next(request)
        
        # Get user's plan
        plan = await self._get_user_plan(user)
        if not plan:
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "Unable to determine user plan"}
            )
        
        # Generate request ID for concurrent tracking
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        request.state.user_id = user.id
        
        # Check rate limits
        is_allowed, rate_info = await self.rate_limit_service.check_rate_limit(user, plan)
        
        if not is_allowed:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Rate limit exceeded",
                    "rate_limit_info": rate_info
                },
                headers={
                    "X-RateLimit-Limit": str(rate_info["limits"]["per_minute"]),
                    "X-RateLimit-Remaining": str(max(0, rate_info["limits"]["per_minute"] - rate_info["requests_per_minute"])),
                    "X-RateLimit-Reset": str(int(rate_info["reset_times"]["minute"].timestamp())),
                    "Retry-After": "60"
                }
            )
        
        # Check concurrent requests
        if not await self.rate_limit_service.check_concurrent_requests(user.id, plan):
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Too many concurrent requests",
                    "concurrent_limit": plan.concurrent_requests
                }
            )
        
        # Acquire concurrent slot
        await self.rate_limit_service.acquire_concurrent_slot(user.id, request_id)
        
        try:
            # Process request
            response = await call_next(request)
            
            # Only increment usage for successful requests (2xx status codes)
            if 200 <= response.status_code < 300:
                await self.rate_limit_service.increment_usage(user.id)
            
            # Add rate limit headers to response
            current_status = await self.rate_limit_service.get_user_rate_limit_status(user, plan)
            response.headers["X-RateLimit-Limit"] = str(current_status["limits"]["per_minute"])
            response.headers["X-RateLimit-Remaining"] = str(current_status["remaining"]["per_minute"])
            response.headers["X-RateLimit-Reset"] = str(current_status["reset_times"]["minute"])
            
            return response
            
        except Exception as e:
            # If there's an error, still increment usage to prevent abuse
            await self.rate_limit_service.increment_usage(user.id)
            raise e
        
        finally:
            # Always release concurrent slot
            await self.rate_limit_service.release_concurrent_slot(user.id, request_id)
    
    async def _get_user_from_request(self, request: Request) -> User:
        """Extract user from request token."""
        try:
            # Get authorization header
            auth_header = request.headers.get("authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                return None
            
            # Extract token
            token = auth_header.split(" ")[1]
            
            # Verify token
            payload = verify_token(token)
            if not payload:
                return None
            
            user_id = payload.get("sub")
            if not user_id:
                return None
            
            # Get user from database
            db = SessionLocal()
            try:
                user = db.query(User).filter(User.id == int(user_id)).first()
                return user
            finally:
                db.close()
                
        except Exception:
            return None
    
    async def _get_user_plan(self, user: User):
        """Get user's current plan."""
        db = SessionLocal()
        try:
            user_service = UserService(db)
            subscription = user_service.get_user_subscription(user.id)
            
            if subscription:
                return subscription.plan
            else:
                # Default to Free plan
                from app.models.user import Plan
                free_plan = db.query(Plan).filter(Plan.name == "Free").first()
                return free_plan
        finally:
            db.close()
