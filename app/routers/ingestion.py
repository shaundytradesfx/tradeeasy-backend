import logging
import os
from typing import Any, Dict, List

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from .. import crud, models, rss_ingest, schemas
from ..database import get_db
from ..rss_feeds import ALL_FEEDS, FEED_CATEGORIES

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
    Background task to ingest all RSS feeds.
    """
    db = next(get_db())
    rss_ingest.ingest_all_feeds(db)


@router.post("/rss", response_model=Dict[str, str])
async def trigger_rss_ingestion(background_tasks: BackgroundTasks):
    """
    Manually trigger the RSS ingestion process.
    """
    background_tasks.add_task(ingest_rss_feeds)
    return {"status": "RSS ingestion started"}


@router.get("/sources", response_model=List[Dict[str, str]])
async def get_rss_sources():
    """
    Get the list of RSS sources being monitored with their asset categories.
    """
    return [
        {"url": url, "category": FEED_CATEGORIES.get(url, "unknown")}
        for url in ALL_FEEDS
    ]


@router.get("/validate/{feed_index}", response_model=Dict[str, Any])
async def validate_feed(feed_index: int):
    """
    Validate a specific RSS feed by its index in the ALL_FEEDS list.
    """
    if feed_index < 0 or feed_index >= len(ALL_FEEDS):
        return {"valid": False, "error": "Invalid feed index"}

    feed_url = ALL_FEEDS[feed_index]
    is_valid, message = rss_ingest.validate_feed(feed_url)

    return {
        "url": feed_url,
        "valid": is_valid,
        "message": message,
        "category": FEED_CATEGORIES.get(feed_url, "unknown"),
    }


@router.post("/feed/{feed_index}", response_model=Dict[str, Any])
async def ingest_single_feed(feed_index: int, db: Session = Depends(get_db)):
    """
    Manually trigger ingestion for a specific feed by its index.
    """
    if feed_index < 0 or feed_index >= len(ALL_FEEDS):
        return {"error": "Invalid feed index"}

    feed_url = ALL_FEEDS[feed_index]
    entries, articles, errors = rss_ingest.ingest_feed(db, feed_url)

    return {
        "url": feed_url,
        "entries_processed": entries,
        "articles_created": articles,
        "errors": errors,
        "category": FEED_CATEGORIES.get(feed_url, "unknown"),
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
