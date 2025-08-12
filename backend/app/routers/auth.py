from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth import get_current_user
from app.schemas.auth import (
    UserCreate, UserResponse, LoginRequest, TokenResponse, 
    RefreshTokenRequest, PasswordChangeRequest
)
from app.services.auth_service import AuthService
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_create: UserCreate,
    db: Session = Depends(get_db)
):
    """Register a new user."""
    auth_service = AuthService(db)
    user = auth_service.create_user(user_create)
    return user


@router.post("/login", response_model=TokenResponse)
async def login(
    login_request: LoginRequest,
    db: Session = Depends(get_db)
):
    """Login and get access and refresh tokens."""
    auth_service = AuthService(db)
    user = auth_service.authenticate_user(login_request)
    tokens = auth_service.create_tokens(user)
    return tokens


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_request: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """Refresh access token using refresh token."""
    auth_service = AuthService(db)
    tokens = auth_service.refresh_access_token(refresh_request.refresh_token)
    return tokens


@router.post("/logout")
async def logout(
    refresh_request: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """Logout by revoking refresh token."""
    auth_service = AuthService(db)
    success = auth_service.logout_user(refresh_request.refresh_token)
    
    if success:
        return {"message": "Successfully logged out"}
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid refresh token"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """Get current user information."""
    return current_user


@router.post("/change-password")
async def change_password(
    password_change: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Change user password."""
    from app.core.security import verify_password, get_password_hash
    
    # Verify current password
    if not verify_password(password_change.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect current password"
        )
    
    # Update password
    current_user.password_hash = get_password_hash(password_change.new_password)
    db.commit()
    
    # Revoke all refresh tokens for security
    auth_service = AuthService(db)
    auth_service.revoke_all_user_tokens(current_user.id)
    
    return {"message": "Password changed successfully. Please login again."}
