from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from datetime import datetime, timedelta
from app.models.user import User, RefreshToken
from app.core.security import verify_password, get_password_hash, create_access_token, create_refresh_token
from app.schemas.auth import UserCreate, LoginRequest
from app.core.config import settings
import secrets


class AuthService:
    def __init__(self, db: Session):
        self.db = db

    def create_user(self, user_create: UserCreate) -> User:
        """Create a new user."""
        # Check if user already exists
        db_user = self.db.query(User).filter(User.email == user_create.email).first()
        if db_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Create new user
        hashed_password = get_password_hash(user_create.password)
        db_user = User(
            email=user_create.email,
            password_hash=hashed_password
        )
        
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)
        
        return db_user

    def authenticate_user(self, login_request: LoginRequest) -> User:
        """Authenticate a user."""
        user = self.db.query(User).filter(User.email == login_request.email).first()
        
        if not user or not verify_password(login_request.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password"
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive user"
            )
        
        return user

    def create_tokens(self, user: User) -> dict:
        """Create access and refresh tokens for a user."""
        access_token = create_access_token(data={"sub": str(user.id)})
        refresh_token_str = create_refresh_token(data={"sub": str(user.id)})
        
        # Store refresh token in database
        refresh_token = RefreshToken(
            token=refresh_token_str,
            user_id=user.id,
            expires_at=datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days)
        )
        
        self.db.add(refresh_token)
        self.db.commit()
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token_str,
            "token_type": "bearer"
        }

    def refresh_access_token(self, refresh_token_str: str) -> dict:
        """Refresh an access token using a refresh token."""
        # Find refresh token in database
        refresh_token = self.db.query(RefreshToken).filter(
            RefreshToken.token == refresh_token_str,
            RefreshToken.is_revoked == False,
            RefreshToken.expires_at > datetime.utcnow()
        ).first()
        
        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        # Get user
        user = self.db.query(User).filter(User.id == refresh_token.user_id).first()
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user"
            )
        
        # Revoke old refresh token
        refresh_token.is_revoked = True
        
        # Create new tokens
        access_token = create_access_token(data={"sub": str(user.id)})
        new_refresh_token_str = create_refresh_token(data={"sub": str(user.id)})
        
        # Store new refresh token
        new_refresh_token = RefreshToken(
            token=new_refresh_token_str,
            user_id=user.id,
            expires_at=datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days)
        )
        
        self.db.add(new_refresh_token)
        self.db.commit()
        
        return {
            "access_token": access_token,
            "refresh_token": new_refresh_token_str,
            "token_type": "bearer"
        }

    def logout_user(self, refresh_token_str: str) -> bool:
        """Logout a user by revoking their refresh token."""
        refresh_token = self.db.query(RefreshToken).filter(
            RefreshToken.token == refresh_token_str,
            RefreshToken.is_revoked == False
        ).first()
        
        if refresh_token:
            refresh_token.is_revoked = True
            self.db.commit()
            return True
        
        return False

    def revoke_all_user_tokens(self, user_id: int) -> None:
        """Revoke all refresh tokens for a user."""
        self.db.query(RefreshToken).filter(
            RefreshToken.user_id == user_id,
            RefreshToken.is_revoked == False
        ).update({"is_revoked": True})
        self.db.commit()
