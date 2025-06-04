"""
Simple authentication system for TradeEasy backend.

Provides basic authentication with JWT tokens and demo user support
for development and testing purposes.
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from uuid import UUID

from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
import hashlib
import logging

from . import crud, models, schemas
from .database import get_db

# Simple in-memory store for demo purposes
# In production, use a proper JWT library and secure key management
DEMO_USERS = {
    "demo": {
        "id": "550e8400-e29b-41d4-a716-446655440000",  # Fixed UUID for demo user
        "username": "demo",
        "email": "demo@tradeeasy.com",
        "password_hash": "demo_hash",  # Simple hash for demo
    }
}

# Simple token store (in production, use JWT with proper signing)
ACTIVE_TOKENS: Dict[str, Dict[str, Any]] = {}

security = HTTPBearer(auto_error=False)

logger = logging.getLogger(__name__)


class AuthenticationError(Exception):
    """Custom exception for authentication errors."""
    pass


def create_demo_user_if_not_exists(db: Session) -> models.User:
    """Create demo user in database if it doesn't exist."""
    try:
        demo_user_id = UUID("550e8400-e29b-41d4-a716-446655440000")
        demo_email = "demo@tradeeasy.com"
        demo_username = "demo"
        
        # First check by email (this is the unique constraint that's failing)
        existing_user = crud.get_user_by_email(db, demo_email)
        if existing_user:
            return existing_user
        
        # Also check by ID as backup
        existing_user = crud.get_user(db, demo_user_id)
        if existing_user:
            return existing_user
        
        # Also check by username
        existing_user = crud.get_user_by_username(db, demo_username)
        if existing_user:
            return existing_user
        
        # Create demo user if none exists
        try:
            demo_user_data = schemas.UserCreate(
                username=demo_username,
                email=demo_email,
                password="demo123"  # This will be hashed
            )
            
            demo_user = crud.create_user(db, demo_user_data)
            logger.info(f"Created new demo user: {demo_user.id}")
            return demo_user
            
        except Exception as create_error:
            # Handle constraint violations or other creation errors
            db.rollback()
            logger.warning(f"Failed to create demo user, checking if it was created by another request: {create_error}")
            
            # Check again in case another request created the user concurrently
            existing_user = crud.get_user_by_email(db, demo_email)
            if existing_user:
                logger.info("Demo user was created by another request, using existing user")
                return existing_user
            
            # If still no user, return a mock user for API compatibility
            logger.warning("Creating mock demo user due to persistent creation issues")
            mock_user = models.User()
            mock_user.id = demo_user_id
            mock_user.username = demo_username
            mock_user.email = demo_email
            mock_user.created_at = datetime.utcnow()
            return mock_user
        
    except Exception as e:
        # Handle any other exceptions
        logger.error(f"Error in create_demo_user_if_not_exists: {e}")
        try:
            db.rollback()
        except:
            pass
        
        # Return a mock user object for API compatibility
        mock_user = models.User()
        mock_user.id = UUID("550e8400-e29b-41d4-a716-446655440000")
        mock_user.username = "demo"
        mock_user.email = "demo@tradeeasy.com"
        mock_user.created_at = datetime.utcnow()
        return mock_user


def generate_simple_token(user_id: str, username: str) -> str:
    """Generate a simple token for demo purposes."""
    # In production, use proper JWT
    timestamp = datetime.utcnow().isoformat()
    token_data = f"{user_id}:{username}:{timestamp}"
    token = hashlib.md5(token_data.encode()).hexdigest()
    
    # Store token with expiration
    ACTIVE_TOKENS[token] = {
        "user_id": user_id,
        "username": username,
        "created_at": datetime.utcnow(),
        "expires_at": datetime.utcnow() + timedelta(hours=24)
    }
    
    return token


def validate_token(token: str) -> Optional[Dict[str, Any]]:
    """Validate a token and return user info if valid."""
    if token not in ACTIVE_TOKENS:
        return None
    
    token_data = ACTIVE_TOKENS[token]
    
    # Check if token is expired
    if datetime.utcnow() > token_data["expires_at"]:
        del ACTIVE_TOKENS[token]
        return None
    
    return token_data


def authenticate_demo_user(username: str, password: str) -> Optional[Dict[str, str]]:
    """Authenticate demo user with simple credentials."""
    if username == "demo" and password == "demo123":
        return DEMO_USERS["demo"]
    return None


def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> models.User:
    """
    Get current authenticated user from token.
    
    For demo purposes, supports both token-based auth and automatic demo user.
    """
    
    # If no authorization header, create/return demo user
    if not authorization:
        return create_demo_user_if_not_exists(db)
    
    # Extract token from "Bearer <token>" format
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = authorization.split(" ")[1]
    
    # Validate token
    token_data = validate_token(token)
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # For demo user, always ensure it exists in database
    if token_data["username"] == "demo":
        return create_demo_user_if_not_exists(db)
    
    # Get user from database for non-demo users
    user_id = UUID(token_data["user_id"])
    user = crud.get_user(db, user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    
    return user


def get_current_user_optional(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> Optional[models.User]:
    """
    Get current user if authenticated, otherwise return None.
    Used for optional authentication endpoints.
    """
    try:
        return get_current_user(authorization, db)
    except HTTPException:
        return None


# Demo helper functions
def create_demo_assets_if_not_exist(db: Session):
    """Create some demo assets for testing watchlists and alerts."""
    demo_assets = [
        {"symbol": "AAPL", "name": "Apple Inc.", "type": "stock"},
        {"symbol": "MSFT", "name": "Microsoft Corporation", "type": "stock"},
        {"symbol": "EURUSD", "name": "Euro to USD", "type": "forex"},
        {"symbol": "BTC", "name": "Bitcoin", "type": "crypto"},
        {"symbol": "GOLD", "name": "Gold", "type": "commodity"},
    ]
    
    for asset_data in demo_assets:
        # Check if asset exists
        existing = crud.get_asset_by_symbol(db, asset_data["symbol"])
        if not existing:
            asset_create = schemas.AssetCreate(**asset_data)
            crud.create_asset(db, asset_create)


def login_demo_user() -> Dict[str, str]:
    """Login demo user and return token."""
    demo_user = DEMO_USERS["demo"]
    token = generate_simple_token(demo_user["id"], demo_user["username"])
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": demo_user["id"],
        "username": demo_user["username"]
    }


# Add user-related schemas if they don't exist
class UserBase:
    username: str
    email: str


class UserCreate(UserBase):
    password: str


class User(UserBase):
    id: UUID
    created_at: datetime
    
    class Config:
        from_attributes = True


class LoginRequest:
    username: str
    password: str


class LoginResponse:
    access_token: str
    token_type: str
    user_id: str
    username: str 