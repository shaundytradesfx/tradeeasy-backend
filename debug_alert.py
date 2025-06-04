#!/usr/bin/env python3
"""Debug script to test alert creation."""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal, engine
from app import models, schemas, crud
from uuid import UUID
import uuid

def test_alert_creation():
    """Test alert creation directly."""
    db = SessionLocal()
    
    try:
        # Create tables if they don't exist
        models.Base.metadata.create_all(bind=engine)
        
        # Get or create demo user
        demo_user = crud.get_user_by_email(db, "demo@tradeeasy.com")
        if not demo_user:
            print("Demo user not found, creating...")
            demo_user_data = schemas.UserCreate(
                username="demo",
                email="demo@tradeeasy.com",
                password="demo123"
            )
            demo_user = crud.create_user(db, demo_user_data)
        
        print(f"Demo user: {demo_user.id}")
        
        # Get or create BTC asset
        btc_asset = crud.get_asset_by_symbol(db, "BTC")
        if not btc_asset:
            print("BTC asset not found, creating...")
            btc_asset = crud.create_asset(db, "BTC", "Bitcoin", "crypto")
        
        print(f"BTC asset: {btc_asset.id}")
        
        # Create alert
        alert_data = schemas.AlertCreate(
            user_id=demo_user.id,
            asset_id=btc_asset.id,
            threshold=0.5,
            direction="above"
        )
        
        print(f"Alert data: {alert_data.model_dump()}")
        
        # Test CRUD function
        new_alert = crud.create_alert(db, alert_data)
        print(f"Alert created successfully: {new_alert.id}")
        
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    success = test_alert_creation()
    print(f"Test {'PASSED' if success else 'FAILED'}") 