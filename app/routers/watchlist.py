"""
Watchlist API endpoints for TradeEasy backend.

Provides CRUD operations for user watchlists with authentication support.
"""

import logging
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..auth import get_current_user
from ..database import get_db

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/api/watchlists",
    tags=["watchlists"],
    responses={404: {"description": "Not found"}},
)


@router.get("/", response_model=List[schemas.WatchlistWithAsset])
async def get_user_watchlists(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all watchlists for the current user."""
    try:
        watchlists = crud.get_watchlists_by_user(db, current_user.id)
        
        # Enhance with asset details
        enhanced_watchlists = []
        for watchlist in watchlists:
            asset = crud.get_asset_by_id(db, watchlist.asset_id)
            if asset:
                enhanced = schemas.WatchlistWithAsset(
                    id=watchlist.id,
                    user_id=watchlist.user_id,
                    created_at=watchlist.created_at,
                    asset=asset
                )
                enhanced_watchlists.append(enhanced)
        
        return enhanced_watchlists
        
    except Exception as e:
        # Rollback any failed transactions
        try:
            db.rollback()
        except:
            pass
        
        logger.error(f"Error getting watchlists for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve watchlists"
        )


@router.post("/", response_model=schemas.WatchlistWithAsset)
async def create_watchlist(
    asset_symbol: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add an asset to the user's watchlist."""
    try:
        # Get asset by symbol
        asset = crud.get_asset_by_symbol(db, asset_symbol)
        if not asset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Asset '{asset_symbol}' not found"
            )
        
        # Check if already in watchlist
        existing_watchlists = crud.get_watchlists_by_user(db, current_user.id)
        for watchlist in existing_watchlists:
            if watchlist.asset_id == asset.id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Asset '{asset_symbol}' is already in your watchlist"
                )
        
        # Create watchlist entry
        watchlist_data = schemas.WatchlistCreate(
            user_id=current_user.id,
            asset_id=asset.id
        )
        
        new_watchlist = crud.create_watchlist(db, watchlist_data)
        
        # Return enhanced response
        return schemas.WatchlistWithAsset(
            id=new_watchlist.id,
            user_id=new_watchlist.user_id,
            created_at=new_watchlist.created_at,
            asset=asset
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating watchlist for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create watchlist entry"
        )


@router.delete("/{watchlist_id}")
async def remove_from_watchlist(
    watchlist_id: UUID,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove an asset from the user's watchlist."""
    try:
        # Get watchlist entry
        watchlist = crud.get_watchlist(db, watchlist_id)
        if not watchlist:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Watchlist entry not found"
            )
        
        # Check ownership
        if watchlist.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only remove your own watchlist entries"
            )
        
        # Delete watchlist entry
        success = crud.delete_watchlist(db, watchlist_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to remove watchlist entry"
            )
        
        return {"message": "Asset removed from watchlist successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing watchlist {watchlist_id} for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove watchlist entry"
        )


@router.delete("/by-symbol/{asset_symbol}")
async def remove_from_watchlist_by_symbol(
    asset_symbol: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove an asset from the user's watchlist by symbol."""
    try:
        # Get asset by symbol
        asset = crud.get_asset_by_symbol(db, asset_symbol)
        if not asset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Asset '{asset_symbol}' not found"
            )
        
        # Find watchlist entry
        user_watchlists = crud.get_watchlists_by_user(db, current_user.id)
        watchlist_to_remove = None
        
        for watchlist in user_watchlists:
            if watchlist.asset_id == asset.id:
                watchlist_to_remove = watchlist
                break
        
        if not watchlist_to_remove:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Asset '{asset_symbol}' is not in your watchlist"
            )
        
        # Delete watchlist entry
        success = crud.delete_watchlist(db, watchlist_to_remove.id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to remove watchlist entry"
            )
        
        return {"message": f"Asset '{asset_symbol}' removed from watchlist successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing asset {asset_symbol} from watchlist for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove watchlist entry"
        )


@router.get("/stats")
async def get_watchlist_stats(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get watchlist statistics for the current user."""
    try:
        watchlists = crud.get_watchlists_by_user(db, current_user.id)
        
        # Group by asset type
        type_counts = {}
        for watchlist in watchlists:
            asset = crud.get_asset_by_id(db, watchlist.asset_id)
            if asset:
                asset_type = asset.type
                type_counts[asset_type] = type_counts.get(asset_type, 0) + 1
        
        return {
            "total_assets": len(watchlists),
            "by_type": type_counts,
            "user_id": str(current_user.id)
        }
        
    except Exception as e:
        logger.error(f"Error getting watchlist stats for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve watchlist statistics"
        ) 