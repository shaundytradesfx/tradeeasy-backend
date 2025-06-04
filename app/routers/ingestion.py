import logging
import os
from typing import Any, Dict, List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import crud, models, rss_ingest, schemas
from ..database import get_db
from ..rss_feeds import ALL_FEEDS, FEED_CATEGORIES
from ..metrics import metrics, get_metrics_summary

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/ingestion",
    tags=["ingestion"],
    responses={404: {"description": "Not found"}},
)

# Deprecated: Get RSS sources from environment variable
# Now using the rss_feeds.py module instead
RSS_SOURCES = (
    os.getenv("RSS_SOURCES", "").split(",") if os.getenv("RSS_SOURCES") else []
)
if not RSS_SOURCES:
    RSS_SOURCES = [ALL_FEEDS[0]] if ALL_FEEDS else []


def ingest_rss_feeds():
    """
    Background task to ingest all RSS feeds with enhanced metrics tracking.
    """
    db = next(get_db())
    try:
        stats = rss_ingest.ingest_all_feeds(db)
        logger.info(f"Scheduled ingestion completed: {stats}")
        return stats
    except Exception as e:
        logger.error(f"Scheduled ingestion failed: {e}")
        metrics.record_error('scheduled_ingestion_failed', 'system')
        raise


@router.post("/rss", response_model=Dict[str, str])
async def trigger_rss_ingestion(background_tasks: BackgroundTasks):
    """
    Manually trigger the RSS ingestion process.
    """
    background_tasks.add_task(ingest_rss_feeds)
    return {"status": "RSS ingestion started", "message": "Check /ingestion/status for progress"}


@router.get("/sources", response_model=List[Dict[str, str]])
async def get_rss_sources():
    """
    Get the list of RSS sources being monitored with their asset categories.
    """
    return [
        {"url": url, "category": FEED_CATEGORIES.get(url, "unknown")}
        for url in ALL_FEEDS
    ]


@router.get("/status", response_model=Dict[str, Any])
async def get_ingestion_status():
    """
    Get current ingestion status and metrics summary.
    """
    try:
        current_stats = metrics.get_current_stats()
        metrics_summary = get_metrics_summary()
        
        return {
            "status": "running" if current_stats.get('duration') else "idle",
            "current_run": current_stats,
            "metrics_summary": metrics_summary,
            "active_feeds_count": len(ALL_FEEDS),
            "feed_categories": {
                category: len([url for url, cat in FEED_CATEGORIES.items() if cat == category])
                for category in set(FEED_CATEGORIES.values())
            }
        }
    except Exception as e:
        logger.error(f"Error getting ingestion status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get ingestion status")


@router.get("/validate/{feed_index}", response_model=Dict[str, Any])
async def validate_feed(feed_index: int):
    """
    Validate a specific RSS feed by its index in the ALL_FEEDS list.
    """
    if feed_index < 0 or feed_index >= len(ALL_FEEDS):
        raise HTTPException(status_code=400, detail="Invalid feed index")

    feed_url = ALL_FEEDS[feed_index]
    
    try:
        is_valid, message = rss_ingest.validate_feed(feed_url)

        return {
            "url": feed_url,
            "valid": is_valid,
            "message": message,
            "category": FEED_CATEGORIES.get(feed_url, "unknown"),
            "index": feed_index
        }
    except Exception as e:
        logger.error(f"Error validating feed {feed_url}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to validate feed: {str(e)}")


@router.post("/feed/{feed_index}", response_model=Dict[str, Any])
async def ingest_single_feed(feed_index: int, db: Session = Depends(get_db)):
    """
    Manually trigger ingestion for a specific feed by its index.
    """
    if feed_index < 0 or feed_index >= len(ALL_FEEDS):
        raise HTTPException(status_code=400, detail="Invalid feed index")

    feed_url = ALL_FEEDS[feed_index]
    
    try:
        entries, articles, errors = rss_ingest.ingest_feed(db, feed_url)

        return {
            "url": feed_url,
            "entries_processed": entries,
            "articles_created": articles,
            "errors": errors,
            "category": FEED_CATEGORIES.get(feed_url, "unknown"),
            "index": feed_index,
            "success_rate": (entries - errors) / entries if entries > 0 else 0
        }
    except Exception as e:
        logger.error(f"Error ingesting feed {feed_url}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to ingest feed: {str(e)}")


@router.get("/metrics", response_model=Dict[str, Any])
async def get_ingestion_metrics():
    """
    Get detailed ingestion metrics for monitoring and debugging.
    """
    try:
        return {
            "metrics_summary": get_metrics_summary(),
            "current_run_stats": metrics.get_current_stats(),
            "prometheus_endpoint": "/metrics",
            "metrics_server_port": 8001
        }
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get metrics")


@router.get("/health", response_model=Dict[str, Any])
async def ingestion_health_check():
    """
    Health check endpoint specifically for ingestion system.
    """
    try:
        # Check if we can access the database
        db = next(get_db())
        
        # Check if we can validate at least one feed
        test_feed_url = ALL_FEEDS[0] if ALL_FEEDS else None
        feed_validation_ok = False
        
        if test_feed_url:
            is_valid, _ = rss_ingest.validate_feed(test_feed_url)
            feed_validation_ok = is_valid
        
        # Get basic metrics
        metrics_summary = get_metrics_summary()
        
        return {
            "status": "healthy",
            "database_connection": "ok",
            "feed_validation": "ok" if feed_validation_ok else "warning",
            "active_feeds": len(ALL_FEEDS),
            "last_success_timestamp": metrics_summary.get('last_success_timestamp', 0),
            "total_articles_created": metrics_summary.get('articles_created_total', 0),
            "total_errors": metrics_summary.get('errors_total', 0)
        }
    except Exception as e:
        logger.error(f"Ingestion health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "database_connection": "error",
            "feed_validation": "error"
        }


# For debugging purposes
if __name__ == "__main__":
    # Test with the first feed
    test_feed = ALL_FEEDS[0] if ALL_FEEDS else "https://finance.yahoo.com/news/rssindex"
    print(f"Testing feed: {test_feed}")

    # Parse feed
    entries = rss_ingest.parse_rss_feed(test_feed)
    print(f"Found {len(entries)} entries")

    # Print first 3 entries if available
    for i, entry in enumerate(entries[:3]):
        print(f"Entry {i + 1}: {entry.get('title', 'No title')}")
