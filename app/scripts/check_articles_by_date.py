#!/usr/bin/env python
"""
Check distribution of articles by date.

This script checks the number of articles created on each day over the past week.
"""

from datetime import datetime, timedelta
import sys
from pathlib import Path

# Add the project root to the path so we can import our app modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.database import SessionLocal
from app import crud

def check_article_distribution():
    """Check the distribution of articles by date."""
    # Create database session
    db = SessionLocal()
    
    try:
        # Get end date (current time)
        end_date = datetime.now()
        
        # Check past week
        print("Article distribution over the past week:")
        print("----------------------------------------")
        
        total_articles = 0
        
        # Loop through each day
        for i in range(7, -1, -1):
            # Calculate day range
            day = end_date - timedelta(days=i)
            next_day = day + timedelta(days=1)
            
            # Get articles for this day
            articles = crud.get_articles_by_date_range(db, day, next_day)
            count = len(articles)
            total_articles += count
            
            # Print results
            print(f"{day.strftime('%Y-%m-%d')}: {count} articles")
        
        print("----------------------------------------")
        print(f"Total: {total_articles} articles")
        
    finally:
        db.close()

if __name__ == "__main__":
    check_article_distribution() 