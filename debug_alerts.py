#!/usr/bin/env python3
"""Debug script to test alerts CRUD functions."""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal, engine
from app import models, schemas, crud
from uuid import UUID
import uuid

def test_alerts_crud():
    """Test alerts CRUD functions directly."""
    db = SessionLocal()
    
    try:
        # Create tables if they don't exist
        models.Base.metadata.create_all(bind=engine)
        
        # Get demo user
        demo_user = crud.get_user_by_email(db, "demo@tradeeasy.com")
        if not demo_user:
            print("Demo user not found!")
            return False
        
        print(f"Demo user: {demo_user.id}")
        
        # Test get_alerts_by_user
        print("Testing get_alerts_by_user...")
        alerts = crud.get_alerts_by_user(db, demo_user.id)
        print(f"Found {len(alerts)} alerts")
        
        for alert in alerts:
            print(f"Alert: {alert.id}, asset_id: {alert.asset_id}, threshold: {alert.threshold}")
            
            # Test getting asset for this alert
            asset = crud.get_asset_by_id(db, alert.asset_id)
            if asset:
                print(f"  Asset: {asset.symbol} ({asset.name})")
            else:
                print(f"  Asset not found for ID: {alert.asset_id}")
        
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    success = test_alerts_crud()
    print(f"Test {'PASSED' if success else 'FAILED'}") 