#!/usr/bin/env python3

"""
Debug script to identify which imports are causing the hanging issue.
This will test imports one by one to isolate the problem.
"""

import sys
import time

def test_import(module_name, description):
    """Test importing a module and time how long it takes."""
    print(f"Testing {description}...")
    start_time = time.time()
    try:
        if module_name == "app.main":
            from app import main
        elif module_name == "app.database":
            from app import database
        elif module_name == "app.models":
            from app import models
        elif module_name == "app.rss_ingest":
            from app import rss_ingest
        elif module_name == "app.websocket_manager":
            from app import websocket_manager
        elif module_name == "app.crud":
            from app import crud
        elif module_name == "app.routers.sentiment":
            from app.routers import sentiment
        elif module_name == "fastapi":
            import fastapi
        elif module_name == "sqlalchemy":
            import sqlalchemy
        elif module_name == "apscheduler":
            from apscheduler.schedulers.asyncio import AsyncIOScheduler
        else:
            __import__(module_name)
        
        duration = time.time() - start_time
        print(f"✅ {description} imported successfully in {duration:.2f}s")
        return True
    except Exception as e:
        duration = time.time() - start_time
        print(f"❌ {description} failed to import in {duration:.2f}s: {e}")
        return False

def main():
    """Test imports systematically."""
    print("=== Import Debug Test ===")
    
    tests = [
        ("fastapi", "FastAPI framework"),
        ("sqlalchemy", "SQLAlchemy ORM"),
        ("apscheduler", "APScheduler"),
        ("app.database", "Database module"),
        ("app.models", "Database models"),
        ("app.rss_ingest", "RSS ingestion module"),
        ("app.websocket_manager", "WebSocket manager"),
        ("app.crud", "CRUD operations"),
        ("app.routers.sentiment", "Sentiment router"),
        ("app.main", "Main application module"),
    ]
    
    for module_name, description in tests:
        success = test_import(module_name, description)
        if not success:
            print(f"❌ FOUND ISSUE: {description} is causing import problems!")
            break
        time.sleep(0.5)  # Small delay between tests
    
    print("=== Import Debug Complete ===")

if __name__ == "__main__":
    main() 