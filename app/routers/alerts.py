"""
Alerts API endpoints for TradeEasy backend.

Provides CRUD operations for user alerts with authentication support
and alert triggering functionality.
"""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..auth import get_current_user
from ..database import get_db

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/api/alerts",
    tags=["alerts"],
    responses={404: {"description": "Not found"}},
)


@router.get("/", response_model=List[schemas.AlertWithAsset])
async def get_user_alerts(
    active_only: bool = Query(False, description="Return only active alerts"),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all alerts for the current user."""
    try:
        alerts = crud.get_alerts_by_user(db, current_user.id, active_only=active_only)
        
        # Enhance with asset details
        enhanced_alerts = []
        for alert in alerts:
            asset = crud.get_asset_by_id(db, alert.asset_id)
            if asset:
                enhanced = schemas.AlertWithAsset(
                    id=alert.id,
                    user_id=alert.user_id,
                    asset_id=alert.asset_id,
                    threshold=alert.threshold,
                    direction=alert.direction,
                    created_at=alert.created_at,
                    triggered_at=alert.triggered_at,
                    is_active=alert.is_active,
                    asset=asset
                )
                enhanced_alerts.append(enhanced)
        
        return enhanced_alerts
        
    except Exception as e:
        # Rollback any failed transactions
        try:
            db.rollback()
        except:
            pass
        
        logger.error(f"Error getting alerts for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve alerts"
        )


@router.post("/", response_model=schemas.AlertWithAsset)
async def create_alert(
    asset_symbol: str,
    threshold: float,
    direction: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new alert for the user."""
    try:
        logger.info(f"Starting alert creation for user: {current_user.id}, asset: {asset_symbol}")
        
        # Validate direction
        if direction not in ["above", "below"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Direction must be either 'above' or 'below'"
            )
        
        logger.info(f"Direction validation passed: {direction}")
        
        # Get asset by symbol
        asset = crud.get_asset_by_symbol(db, asset_symbol)
        if not asset:
            logger.error(f"Asset not found: {asset_symbol}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Asset '{asset_symbol}' not found"
            )
        
        logger.info(f"Asset found: {asset.id}")
        
        # Validate threshold
        if threshold < -1.0 or threshold > 1.0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Threshold must be between -1.0 and 1.0 (sentiment score range)"
            )
        
        logger.info(f"Threshold validation passed: {threshold}")
        
        # Create alert
        alert_data = schemas.AlertCreate(
            user_id=current_user.id,
            asset_id=asset.id,
            threshold=threshold,
            direction=direction
        )
        
        logger.info(f"Alert data created: {alert_data.model_dump()}")
        
        new_alert = crud.create_alert(db, alert_data)
        
        logger.info(f"Alert created successfully: {new_alert.id}")
        
        # Return enhanced response
        return schemas.AlertWithAsset(
            id=new_alert.id,
            user_id=new_alert.user_id,
            asset_id=new_alert.asset_id,
            threshold=new_alert.threshold,
            direction=new_alert.direction,
            created_at=new_alert.created_at,
            triggered_at=new_alert.triggered_at,
            is_active=new_alert.is_active,
            asset=asset
        )
        
    except HTTPException:
        raise
    except Exception as e:
        # Rollback any failed transactions
        try:
            db.rollback()
        except:
            pass
        
        logger.error(f"Error creating alert for user {current_user.id}: {e}")
        logger.error(f"Alert data: asset_symbol={asset_symbol}, threshold={threshold}, direction={direction}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create alert"
        )


@router.delete("/{alert_id}")
async def delete_alert(
    alert_id: UUID,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete an alert."""
    try:
        # Get alert
        alert = crud.get_alert(db, alert_id)
        if not alert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Alert not found"
            )
        
        # Check ownership
        if alert.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only delete your own alerts"
            )
        
        # Delete alert
        success = crud.delete_alert(db, alert_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete alert"
            )
        
        return {"message": "Alert deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting alert {alert_id} for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete alert"
        )


@router.post("/{alert_id}/reset")
async def reset_alert(
    alert_id: UUID,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Reset a triggered alert to active state."""
    try:
        # Get alert
        alert = crud.get_alert(db, alert_id)
        if not alert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Alert not found"
            )
        
        # Check ownership
        if alert.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only reset your own alerts"
            )
        
        # Reset alert
        reset_alert = crud.reset_alert(db, alert_id)
        if not reset_alert:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to reset alert"
            )
        
        return {"message": "Alert reset successfully", "alert_id": str(alert_id)}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resetting alert {alert_id} for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reset alert"
        )


@router.get("/triggered", response_model=List[schemas.AlertWithAsset])
async def get_triggered_alerts(
    limit: int = Query(50, le=100, description="Maximum number of alerts to return"),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get recently triggered alerts for the current user."""
    try:
        triggered_alerts = crud.get_triggered_alerts(db, current_user.id, limit)
        
        # Enhance with asset details
        enhanced_alerts = []
        for alert in triggered_alerts:
            asset = crud.get_asset_by_id(db, alert.asset_id)
            if asset:
                enhanced = schemas.AlertWithAsset(
                    id=alert.id,
                    user_id=alert.user_id,
                    asset_id=alert.asset_id,
                    threshold=alert.threshold,
                    direction=alert.direction,
                    created_at=alert.created_at,
                    triggered_at=alert.triggered_at,
                    is_active=alert.is_active,
                    asset=asset
                )
                enhanced_alerts.append(enhanced)
        
        return enhanced_alerts
        
    except Exception as e:
        logger.error(f"Error getting triggered alerts for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve triggered alerts"
        )


@router.get("/stats")
async def get_alert_stats(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get alert statistics for the current user."""
    try:
        all_alerts = crud.get_alerts_by_user(db, current_user.id, active_only=False)
        active_alerts = crud.get_alerts_by_user(db, current_user.id, active_only=True)
        triggered_alerts = crud.get_triggered_alerts(db, current_user.id)
        
        # Count by direction
        direction_counts = {"above": 0, "below": 0}
        asset_type_counts = {}
        
        for alert in all_alerts:
            direction_counts[alert.direction] += 1
            
            # Get asset type
            asset = crud.get_asset_by_id(db, alert.asset_id)
            if asset:
                asset_type = asset.type
                asset_type_counts[asset_type] = asset_type_counts.get(asset_type, 0) + 1
        
        return {
            "total_alerts": len(all_alerts),
            "active_alerts": len(active_alerts),
            "triggered_alerts": len(triggered_alerts),
            "by_direction": direction_counts,
            "by_asset_type": asset_type_counts,
            "user_id": str(current_user.id)
        }
        
    except Exception as e:
        logger.error(f"Error getting alert stats for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve alert statistics"
        )


@router.post("/test-trigger")
async def test_alert_trigger(
    asset_symbol: str,
    sentiment_score: float,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Test alert triggering for a specific asset and sentiment score."""
    try:
        # Check and trigger alerts
        triggered_alert_ids = crud.check_and_trigger_alerts(db, asset_symbol, sentiment_score)
        
        return {
            "asset_symbol": asset_symbol,
            "sentiment_score": sentiment_score,
            "triggered_alerts": len(triggered_alert_ids),
            "triggered_alert_ids": [str(alert_id) for alert_id in triggered_alert_ids]
        }
        
    except Exception as e:
        logger.error(f"Error testing alert trigger for {asset_symbol}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to test alert trigger"
        )


@router.get("/test-simple")
async def test_simple_alerts(db: Session = Depends(get_db)):
    """Simple test endpoint without authentication."""
    try:
        # Get demo user directly
        demo_user = crud.get_user_by_email(db, "demo@tradeeasy.com")
        if not demo_user:
            return {"error": "Demo user not found"}
        
        # Get alerts for demo user
        alerts = crud.get_alerts_by_user(db, demo_user.id)
        
        return {
            "user_id": str(demo_user.id),
            "alert_count": len(alerts),
            "alerts": [
                {
                    "id": str(alert.id),
                    "asset_id": str(alert.asset_id),
                    "threshold": alert.threshold,
                    "direction": alert.direction
                }
                for alert in alerts
            ]
        }
        
    except Exception as e:
        import traceback
        return {
            "error": str(e),
            "traceback": traceback.format_exc()
        }


@router.get("/debug-user")
async def debug_current_user(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Debug endpoint to check current user."""
    try:
        return {
            "user_id": str(current_user.id),
            "username": current_user.username,
            "email": current_user.email,
            "user_type": type(current_user).__name__,
            "has_id": hasattr(current_user, 'id'),
            "id_type": type(current_user.id).__name__ if hasattr(current_user, 'id') else None
        }
    except Exception as e:
        logger.error(f"Error in debug endpoint: {e}")
        return {"error": str(e)} 