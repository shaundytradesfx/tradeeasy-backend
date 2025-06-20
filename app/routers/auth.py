"""
Authentication API endpoints for TradeEasy backend.

Provides login/logout functionality with JWT authentication.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import schemas, models
from ..auth import authenticate_user, create_access_token, create_demo_assets_if_not_exist, get_current_user
from ..database import get_db

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/api/auth",
    tags=["authentication"],
    responses={404: {"description": "Not found"}},
)


@router.post("/login", response_model=schemas.LoginResponse)
async def login(
    login_request: schemas.LoginRequest,
    db: Session = Depends(get_db)
):
    """
    Authenticate user and return JWT access token.
    
    For demo purposes, supports username='demo' and password='demo123'.
    """
    try:
        # Authenticate user with new JWT system
        user = authenticate_user(db, login_request.username, login_request.password)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Create demo assets if they don't exist
        create_demo_assets_if_not_exist(db)
        
        # Generate JWT token
        access_token = create_access_token(
            data={"sub": str(user.id), "username": user.username}
        )
        
        logger.info(f"User {login_request.username} logged in successfully")
        
        return schemas.LoginResponse(
            access_token=access_token,
            token_type="bearer",
            user_id=str(user.id),
            username=user.username
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error for user {login_request.username}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


@router.post("/logout")
async def logout():
    """
    Logout user.
    
    Note: With JWT tokens, logout is typically handled client-side by discarding the token.
    In a production system, you might implement token blacklisting.
    """
    return {"message": "Logged out successfully"}


@router.get("/demo-login", response_model=schemas.LoginResponse)
async def demo_login(db: Session = Depends(get_db)):
    """
    Quick demo login endpoint that logs in the demo user automatically.
    
    Useful for testing and development.
    """
    try:
        # Create demo assets if they don't exist
        create_demo_assets_if_not_exist(db)
        
        # Authenticate demo user
        demo_user = authenticate_user(db, "demo", "demo123")
        if not demo_user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Demo user authentication failed"
            )
        
        # Generate JWT token for demo user
        access_token = create_access_token(
            data={"sub": str(demo_user.id), "username": demo_user.username}
        )
        
        logger.info("Demo user logged in via quick login")
        
        return schemas.LoginResponse(
            access_token=access_token,
            token_type="bearer",
            user_id=str(demo_user.id),
            username=demo_user.username
        )
        
    except Exception as e:
        logger.error(f"Demo login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Demo login failed"
        )


@router.get("/status")
async def auth_status():
    """Get authentication system status."""
    return {
        "auth_type": "JWT",
        "algorithm": "HS256",
        "token_expiry_minutes": 1440,  # 24 hours
        "demo_user_available": True,
        "demo_credentials": {
            "username": "demo",
            "password": "demo123"
        },
        "endpoints": {
            "login": "/api/auth/login",
            "logout": "/api/auth/logout",
            "demo_login": "/api/auth/demo-login"
        },
        "security_features": [
            "JWT tokens",
            "bcrypt password hashing",
            "Token expiration",
            "Bearer token authentication"
        ]
    }


@router.post("/admin/create-indexes")
async def create_database_indexes(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create performance indexes on the database.
    
    This endpoint is useful for upgrading existing databases with performance indexes.
    Requires authentication.
    """
    try:
        from ..database import create_performance_indexes
        
        # Create indexes using the database engine
        created_count = create_performance_indexes(db.bind)
        
        logger.info(f"User {current_user.username} triggered index creation: {created_count} indexes created")
        
        return {
            "message": "Database index creation completed",
            "indexes_created": created_count,
            "user": current_user.username,
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Database index creation failed for user {current_user.username}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create database indexes: {str(e)}"
        ) 