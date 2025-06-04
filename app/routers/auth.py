"""
Authentication API endpoints for TradeEasy backend.

Provides login/logout functionality with demo user support.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import schemas
from ..auth import authenticate_demo_user, login_demo_user, create_demo_assets_if_not_exist
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
    Authenticate user and return access token.
    
    For demo purposes, supports username='demo' and password='demo123'.
    """
    try:
        # Authenticate user
        user_data = authenticate_demo_user(login_request.username, login_request.password)
        
        if not user_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Create demo assets if they don't exist
        create_demo_assets_if_not_exist(db)
        
        # Generate token and return response
        token_data = login_demo_user()
        
        logger.info(f"User {login_request.username} logged in successfully")
        
        return schemas.LoginResponse(
            access_token=token_data["access_token"],
            token_type=token_data["token_type"],
            user_id=token_data["user_id"],
            username=token_data["username"]
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
    Logout user (for demo purposes, just returns success message).
    
    In a real implementation, this would invalidate the token.
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
        
        # Generate token for demo user
        token_data = login_demo_user()
        
        logger.info("Demo user logged in via quick login")
        
        return schemas.LoginResponse(
            access_token=token_data["access_token"],
            token_type=token_data["token_type"],
            user_id=token_data["user_id"],
            username=token_data["username"]
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
        "auth_type": "demo",
        "demo_user_available": True,
        "demo_credentials": {
            "username": "demo",
            "password": "demo123"
        },
        "endpoints": {
            "login": "/api/auth/login",
            "logout": "/api/auth/logout",
            "demo_login": "/api/auth/demo-login"
        }
    } 